# config.py
import os
from dataclasses import dataclass

@dataclass
class Config:
    # Настройки папки
    WATCH_FOLDER = os.getenv("WATCH_FOLDER", "./app/audio_uploads")
    PROCESSING_FOLDER = os.getenv("PROCESSING_FOLDER", "./app/processing")
    PROCESSED_FOLDER = os.getenv("PROCESSED_FOLDER", "./app/processed")
    JSON_FOLDER = os.getenv("JSON_FOLDER", "./app/json_output")
    
    # Настройки API
    BACKEND_API_BASE = os.getenv("BACKEND_API", "http://api:8000/api")
    API_ENDPOINT = os.getenv("API_ENDPOINT", "http://api:8000/api/conversations")
    
    # Настройки транскрипции
    TRANSCRIPTION_SERVICE_URL = "https://demo.connect2ai.net/spr/stt/big"
    AUTORIZATION_SERVICE_URL = os.getenv("AUTORIZATION_SERVICE_URL", "https://demo.connect2ai.net/spr/auth/signin")
    TRANSCRIPTION_ACCESS_TOKEN = os.getenv("TRANSCRIPTION_ACCESS_TOKEN", "")
    LOGIN = os.getenv("LOGIN", "")
    PASSWORD = os.getenv("PASSWORD", "")
    
    # Настройки многопоточности
    MAX_WORKERS = int(os.getenv("MAX_WORKERS", 3))
    QUEUE_CHECK_INTERVAL = int(os.getenv("QUEUE_CHECK_INTERVAL", 2))
    
    # Настройки логирования
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    TRANSCRIPTION_TIMEOUT = 300
    API_TIMEOUT = 30  # Таймаут для API запросов
    MAX_RETRIES = 3

    API_MAX_RETRIES = 3  # Повторные попытки для API

