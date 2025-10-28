"""
Улучшенный файл настроек приложения.
Использует Pydantic для валидации и типизации.
"""
import os
from pathlib import Path
from typing import Optional, Set

from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    """
    Настройки приложения для обработки аудио.
    
    Все переменные могут быть переопределены через переменные окружения
    или загружены из файла .env в корне проекта.
    """
    
    # ========== ПУТИ К ФАЙЛАМ ==========
    
    BASE_DIR: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent,
        description="Корневая директория проекта"
    )
    
    STORAGE_DIR: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent / "storage",
        description="Базовая директория для хранения"
    )
    
    UPLOAD_DIR: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent / "storage" / "audio_uploads",
        description="Папка для входящих аудиофайлов"
    )
    
    PROCESSING_DIR: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent / "storage" / "processing",
        description="Временная папка для файлов в процессе обработки"
    )
    
    PROCESSED_DIR: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent / "storage" / "processed",
        description="Папка для обработанных аудиофайлов"
    )
    
    JSON_OUTPUT_DIR: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent / "storage" / "json_output",
        description="Папка для JSON файлов с результатами"
    )
    
    # ========== НАСТРОЙКИ API ==========
    
    BACKEND_API_BASE: str = Field(
        default="http://api:8000/api",
        description="Базовый URL для отправки результатов"
    )
    
    API_ENDPOINT: str = Field(
        default="http://api:8000/api/conversations",
        description="Эндпоинт для отправки результатов транскрипции"
    )
    
    # ========== НАСТРОЙКИ ТРАНСКРИПЦИИ ==========
    
    TRANSCRIPTION_SERVICE_URL: str = Field(
        default="https://demo.connect2ai.net/spr/stt/big",
        description="URL сервиса транскрипции"
    )
    TRANSCRIPTION_SERVICE_BY_JOB_URL: str = Field(
        default="https://demo.connect2ai.net/spr/result",
        description="URL сервиса результата транскрипции"
    )
    AUTHORIZATION_SERVICE_URL: str = Field(
        default="https://demo.connect2ai.net/auth/access",
        description="URL сервиса авторизации"
    )
    
    TRANSCRIPTION_ACCESS_TOKEN: Optional[str] = Field(
        default=None,
        description="Access token для сервиса транскрипции (если есть)"
    )
    
    LOGIN: Optional[str] = Field(
        default=None,
        description="Логин для аутентификации в сервисе"
    )
    
    PASSWORD: Optional[str] = Field(
        default=None,
        description="Пароль для аутентификации в сервисе"
    )
    
    # ========== НАСТРОЙКИ ПАРАЛЛЕЛИЗМА ==========
    
    MAX_CONCURRENT_TASKS: int = Field(
        default=3,
        ge=1,
        le=20,
        description="Количество одновременных async задач обработки"
    )
    
    MAX_TRANSCRIPTION_CALLS: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Максимум одновременных запросов к API транскрипции"
    )
    
    MAX_API_CALLS: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Максимум одновременных отправок на backend API"
    )
    
    TASK_QUEUE_MAX_SIZE: int = Field(
        default=100,
        ge=10,
        le=1000,
        description="Максимальный размер очереди задач"
    )
    
    QUEUE_CHECK_INTERVAL: int = Field(
        default=2,
        ge=1,
        le=10,
        description="Интервал сканирования папки на новые файлы (секунды)"
    )
    
    # ========== ТАЙМАУТЫ И ПОВТОРЫ ==========
    
    TRANSCRIPTION_TIMEOUT: int = Field(
        default=300,
        ge=60,
        le=3600,
        description="Таймаут для одного запроса транскрипции (секунды)"
    )
    
    API_TIMEOUT: int = Field(
        default=30,
        ge=10,
        le=300,
        description="Таймаут для API запросов (секунды)"
    )
    
    API_MAX_RETRIES: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Максимальное количество попыток повтора при ошибке"
    )
    
    # ========== ЛИМИТЫ ФАЙЛОВ ==========
    
    MAX_FILE_SIZE_BYTES: int = Field(
        default=500 * 1024 * 1024,  # 500 MB
        description="Максимальный размер аудиофайла (байты)"
    )
    
    SUPPORTED_AUDIO_FORMATS: Set[str] = Field(
        default={'.wav', '.mp3', '.m4a', '.flac', '.ogg', '.aac', '.wma'},
        description="Поддерживаемые расширения аудиофайлов"
    )
    
    # ========== ЛОГИРОВАНИЕ ==========
    
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    
    LOG_FORMAT: str = Field(
        default="json",
        description="Формат логирования (json или text)"
    )
    
    # ========== ДРУГОЕ ==========
    
    DEBUG: bool = Field(
        default=False,
        description="Режим отладки"
    )
    
    @validator('LOG_LEVEL')
    def validate_log_level(cls, v: str) -> str:
        allowed_levels = {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}
        if v.upper() not in allowed_levels:
            raise ValueError(f'LOG_LEVEL должен быть одним из: {allowed_levels}')
        return v.upper()
    
    def ensure_directories(self) -> None:
        """Создать все необходимые директории"""
        for directory in [
            self.STORAGE_DIR,
            self.UPLOAD_DIR,
            self.PROCESSING_DIR,
            self.PROCESSED_DIR,
            self.JSON_OUTPUT_DIR
        ]:
            directory.mkdir(parents=True, exist_ok=True)
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        env_file_encoding = 'utf-8'


# Глобальный экземпляр настроек
settings = Settings()

# Создаем директории при импорте
settings.ensure_directories()
