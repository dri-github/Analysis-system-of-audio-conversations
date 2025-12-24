from fastapi import FastAPI, HTTPException, Body, Query, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from typing import Dict, Any
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
import uvicorn

from datetime import timedelta
from database import get_db, Base, engine
from models import User, Conversation
from auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user,
    Token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    TokenData
)
from stats import calculate_stats

# --- Lifespan для создания таблиц ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: создание всех таблиц (если их нет)
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown: можно добавить код для закрытия соединений


app = FastAPI(title="Conversations API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешить всем источникам (в продакшене укажите конкретные домены)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic модели для запросов/ответов ---
class UserRegister(BaseModel):
    username: str
    email: str
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    username: str
    email: str


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    file_data: Dict[str, Any]
    file_name: str
    file_path: str
    date_time: str


# --- Эндпоинты авторизации ---

@app.post("/api/auth/register", response_model=dict, status_code=status.HTTP_201_CREATED)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """Регистрация нового пользователя"""
    # Проверка существования пользователя
    existing_user = db.query(User).filter(
        (User.username == user_data.username) | (User.email == user_data.email)
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered"
        )
    
    # Хеширование пароля и создание пользователя
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password
    )
    
    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return {
            "message": "User registered successfully",
            "user": {
                "id": new_user.id,
                "username": new_user.username,
                "email": new_user.email
            }
        }
    except Exception as e:
        db.rollback()
        import traceback
        error_detail = str(e)
        # Логируем полную ошибку для отладки
        print(f"Registration error: {error_detail}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating user: {error_detail}"
        )


@app.post("/api/auth/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Вход пользователя и получение JWT токена"""
    # Поиск пользователя по username
    user = db.query(User).filter(User.username == form_data.username).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Проверка пароля
    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Создание токена
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/api/auth/me", response_model=UserResponse)
def read_users_me(current_user: TokenData = Depends(get_current_user), db: Session = Depends(get_db)):
    """Получение информации о текущем пользователе"""
    user = db.query(User).filter(User.username == current_user.username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


# --- Эндпоинты для разговоров ---

@app.post("/api/conversations")
def add_conversation(
    conversation: Dict[str, Any] = Body(...),
    fname: str = Query(...),
    fpath: str = Query(...),
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Добавление нового разговора"""
    try:
        new_conversation = Conversation(
            file_data=conversation,
            file_name=fname,
            file_path=fpath
        )
        db.add(new_conversation)
        db.commit()
        db.refresh(new_conversation)
        return {"id": new_conversation.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/conversations")
def get_all_conversations(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получение списка всех разговоров"""
    conversations = db.query(Conversation).all()
    result = []
    for conv in conversations:
        result.append({
            "id": conv.id,
            "file_data": conv.file_data,
            "file_name": conv.file_name,
            "file_path": conv.file_path,
            "date_time": conv.date_time.isoformat() if conv.date_time else None
        })
    return result


@app.get("/api/conversations/{conversation_id}")
def get_conversation(
    conversation_id: int,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получение конкретного разговора по ID"""
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return {
        "id": conversation.id,
        "file_data": conversation.file_data,
        "file_name": conversation.file_name,
        "file_path": conversation.file_path,
        "date_time": conversation.date_time.isoformat() if conversation.date_time else None
    }


@app.get("/api/analyze/stats/{conversation_id}")
def analyze_stats(
    conversation_id: int,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получение статистики разговора"""
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if not conversation.file_data:
        raise HTTPException(status_code=404, detail="No data")
    
    # Вычисляем статистику из file_data
    stats = calculate_stats(conversation.file_data)
    return stats


# --- Авто-запуск через python main.py ---
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
