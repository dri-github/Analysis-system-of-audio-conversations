from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import databases
import json
import uvicorn  # добавляем

# --- Подключение к PostgreSQL ---
DATABASE_URL = "postgresql://audrec_conv_s:service@localhost:5432/mydb"
database = databases.Database(DATABASE_URL)

app = FastAPI(title="Conversations API")

# --- Pydantic модель для входящего JSON ---
class Conversation(BaseModel):
    file_data: dict

# --- Lifespan для подключения к БД ---
@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

# --- POST /api/conversations ---
@app.post("/api/conversations")
async def add_conversation(conversation: Conversation, fname: str = Query(...), fpath: str = Query(...)):
    query = """
    SELECT public.load_conversation(:file_data::jsonb, :file_name, :file_path) AS id
    """
    values = {
        "file_data": json.dumps(conversation.file_data),
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
async def get_all_conversations():
    query = "SELECT * FROM public.get_conversations()"
    results = await database.fetch_all(query=query)
    return [dict(r) for r in results]

# --- GET /api/conversations/{id} ---
@app.get("/api/conversations/{conversation_id}")
async def get_conversation(conversation_id: int):
    query = "SELECT * FROM public.get_single_conversation(:id)"
    result = await database.fetch_one(query=query, values={"id": conversation_id})
    if not result:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return dict(result)

# --- GET /analyze/stats ---
@app.get("/analyze/stats")
async def analyze_stats():
    query = "SELECT COUNT(*) AS total FROM public.get_conversations()"
    result = await database.fetch_one(query=query)
    return {"total_conversations": result["total"]}

# --- Авто-запуск через python main.py ---
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)



#curl -X POST "http://127.0.0.1:8000/api/conversations?fname=chat1.json&fpath=/data/chat1.json" \
#-H "Content-Type: application/json" \
#-d '{"file_data": {"messages":[{"user":"Alice","text":"Привет"},{"user":"Bob","text":"Привет, как дела?"}]}}'
