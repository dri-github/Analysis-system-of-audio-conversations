# config.py
import os
from dataclasses import dataclass

@dataclass
class Config:
    # Настройки папки
    WATCH_FOLDER = os.getenv("WATCH_FOLDER", "D:/Work/PetProject/audio_processing/app/audio_uploads")
    PROCESSED_FOLDER = os.getenv("PROCESSED_FOLDER", "D:/Work/PetProject/audio_processing/app/processed")
    PROCESSING_FOLDER = os.getenv("PROCESSING_FOLDER", "D:/Work/PetProject/audio_processing/app/processing")
    JSON_FOLDER =os.getenv("PROCESSING_FOLDER", "D:/Work/PetProject/audio_processing/app/json")
    
    # Настройки API
    BACKEND_API_BASE = os.getenv("BACKEND_API", "http://localhost:8000/api")
    TRANSCRIPTION_ENDPOINT = f"{BACKEND_API_BASE}/transcriptions"
    
    # Настройки транскрипции
    AUTORIZATION_SERVICE_URL = "https://demo.connect2ai.net/auth/access" 
    TRANSCRIPTION_SERVICE_URL = "https://demo.connect2ai.net/spr/stt/common"
    TRANSCRIPTION_ACCESS_TOKEN = os.getenv("TRANSCRIPTION_ACCESS_TOKEN", "token")
    MAX_RETRIES = 3
    TRANSCRIPTION_TIMEOUT = 300
    LOGIN = ""
    PASSWORD = ""

    # Настройки многопоточности
    MAX_WORKERS = int(os.getenv("MAX_WORKERS", 3))  # Максимальное количество параллельных воркеров
    QUEUE_CHECK_INTERVAL = int(os.getenv("QUEUE_CHECK_INTERVAL", 2))  # Интервал проверки очереди в секундах

     # Настройки логирования
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_JSON = os.getenv("LOG_JSON", "false").lower() == "true"  # JSON формат для production