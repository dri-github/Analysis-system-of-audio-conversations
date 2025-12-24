from fastapi import FastAPI, HTTPException, Body, Query, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from typing import Optional, Dict, Any
from pydantic import BaseModel
import databases
import json
import uvicorn  # добавляем

from collections import defaultdict, Counter
from datetime import timedelta
from auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user,
    Token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    TokenData
)

# --- Подключение к PostgreSQL ---
DATABASE_URL = "postgresql://audrec_conv_s:service@postgres:5432/audio_rec"
database = databases.Database(DATABASE_URL)

app = FastAPI(title="Conversations API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешить всем источникам (в продакшене укажите конкретные домены)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic модели ---
class Conversation(BaseModel):
    file_data: dict


class UserRegister(BaseModel):
    username: str
    email: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class User(BaseModel):
    id: int
    username: str
    email: str
    hashed_password: str

# --- Lifespan для подключения к БД ---
@app.on_event("startup")
async def startup():
    await database.connect()
    # Создание таблицы пользователей, если её нет
    create_users_table_query = """
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL,
        email VARCHAR(100) UNIQUE NOT NULL,
        hashed_password VARCHAR(255) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    try:
        await database.execute(create_users_table_query)
    except Exception as e:
        print(f"Ошибка при создании таблицы users: {e}")

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()


# --- Эндпоинты авторизации ---

@app.post("/api/auth/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister):
    """Регистрация нового пользователя"""
    # Проверка существования пользователя
    check_user_query = "SELECT id FROM users WHERE username = :username OR email = :email"
    existing_user = await database.fetch_one(
        query=check_user_query,
        values={"username": user_data.username, "email": user_data.email}
    )
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered"
        )
    
    # Хеширование пароля и создание пользователя
    hashed_password = get_password_hash(user_data.password)
    insert_user_query = """
    INSERT INTO users (username, email, hashed_password)
    VALUES (:username, :email, :hashed_password)
    RETURNING id, username, email
    """
    try:
        result = await database.fetch_one(
            query=insert_user_query,
            values={
                "username": user_data.username,
                "email": user_data.email,
                "hashed_password": hashed_password
            }
        )
        return {
            "message": "User registered successfully",
            "user": {
                "id": result["id"],
                "username": result["username"],
                "email": result["email"]
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating user: {str(e)}"
        )


@app.post("/api/auth/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Вход пользователя и получение JWT токена"""
    # Поиск пользователя по username
    get_user_query = "SELECT id, username, email, hashed_password FROM users WHERE username = :username"
    user = await database.fetch_one(
        query=get_user_query,
        values={"username": form_data.username}
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Проверка пароля
    if not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Создание токена
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/api/auth/me")
async def read_users_me(current_user: TokenData = Depends(get_current_user)):
    """Получение информации о текущем пользователе"""
    get_user_query = "SELECT id, username, email FROM users WHERE username = :username"
    user = await database.fetch_one(
        query=get_user_query,
        values={"username": current_user.username}
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return {
        "id": user["id"],
        "username": user["username"],
        "email": user["email"]
    }


# --- POST /api/conversations ---
@app.post("/api/conversations")
async def add_conversation(
    conversation: Dict[str, Any] = Body(...),
    fname: str = Query(...),
    fpath: str = Query(...),
    current_user: TokenData = Depends(get_current_user)
):
    query = """
    SELECT public.load_conversation(CAST(:file_data AS jsonb), :file_name, :file_path) AS id
    """
    values = {
        "file_data": json.dumps(conversation),
        "file_name": fname,
        "file_path": fpath
    }
    try:
        result = await database.fetch_one(query=query, values=values)
        return {"id": result["id"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- GET /api/conversations ---
@app.get("/api/conversations")
async def get_all_conversations(current_user: TokenData = Depends(get_current_user)):
    query = "SELECT * FROM public.get_conversations()"
    results = await database.fetch_all(query=query)
    return [dict(r) for r in results]

# --- GET /api/conversations/{id} ---
@app.get("/api/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: int,
    current_user: TokenData = Depends(get_current_user)
):
    query = "SELECT * FROM public.get_single_conversation(:id)"
    result = await database.fetch_one(query=query, values={"id": conversation_id})
    if not result:
        raise HTTPException(status_code=404, detail="Conversation not found")

    data = dict(result)
    # Парсим file_data из строки в JSON-объект
    if "file_data" in data and isinstance(data["file_data"], str):
        try:
            data["file_data"] = json.loads(data["file_data"])
        except json.JSONDecodeError:
            # Если вдруг невалидный JSON, оставляем как есть
            pass

    return data

# --- GET /analyze/stats ---
#@app.get("/analyze/stats")
#async def analyze_stats():
#    query = "SELECT COUNT(*) AS total FROM public.get_conversations()"
#    result = await database.fetch_one(query=query)
#    return {"total_conversations": result["total"]}

# --- GET /analyze/stats ---
@app.get("/api/analyze/stats/{conversation_id}")
async def analyze_stats(
    conversation_id: int,
    current_user: TokenData = Depends(get_current_user)
):
    query = "SELECT public.get_conversations_stats(:cid) AS stats"
    result = await database.fetch_one(query=query, values={"cid": conversation_id})
    if not result:
        raise HTTPException(status_code=404, detail="No data")
    
    stats = result["stats"]
    if isinstance(stats, str):
        stats = json.loads(stats)
    
    return stats

# --- Авто-запуск через python main.py ---
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
