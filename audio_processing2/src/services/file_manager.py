"""
Управление файлами и директориями приложения.
Упрощенная версия с поддержкой перемещения в папку processing.
"""
import os
import shutil
import json
from pathlib import Path
from typing import Optional, List, Dict, Any

from config.settings import settings
from src.core.exceptions import FileManagementError
import structlog

logger = structlog.get_logger()


class FileManager:
    """Управление файлами и папками приложения"""
    
    def __init__(self):
        """Инициализация менеджера файлов"""
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Создание необходимых директорий"""
        try:
            directories = [
                settings.STORAGE_DIR,
                settings.UPLOAD_DIR,
                settings.PROCESSING_DIR,
                settings.PROCESSED_DIR,
                settings.JSON_OUTPUT_DIR
            ]
            
            for directory in directories:
                directory.mkdir(parents=True, exist_ok=True)
                
            logger.info("directories.verified")
            
        except Exception as e:
            raise FileManagementError(f"Failed to create directories: {e}")

    def get_audio_files(self, directory: Path) -> List[Path]:
        """Получение списка аудиофайлов в директории"""
        try:
            files = [
                file_path 
                for file_path in directory.iterdir()
                if file_path.is_file() 
                and file_path.suffix.lower() in settings.SUPPORTED_AUDIO_FORMATS
            ]
            return files
        except Exception as e:
            logger.error("get.audio.files.error", error=str(e))
            return []

    def validate_audio_file(self, file_path: Path) -> bool:
        """Валидация аудиофайла"""
        try:
            if not file_path.exists():
                return False
            if not file_path.is_file():
                return False
            if file_path.suffix.lower() not in settings.SUPPORTED_AUDIO_FORMATS:
                return False
            
            file_size = file_path.stat().st_size
            if file_size == 0:
                return False
            if file_size > settings.MAX_FILE_SIZE_BYTES:
                return False
            
            return True
        except Exception as e:
            logger.error("validate.audio.file.error", error=str(e))
            return False

    def move_to_processing(self, file_path: Path) -> Optional[Path]:
        """Перемещение файла в папку обработки"""
        try:
            if not file_path.exists():
                logger.warning("move.to.processing.file.not.exists", file=file_path.name)
                return None
                
            destination = settings.PROCESSING_DIR / file_path.name
            shutil.move(str(file_path), str(destination))
            
            logger.info("file.moved.to.processing", 
                       file=file_path.name, 
                       destination=str(destination))
            return destination
            
        except Exception as e:
            logger.error("move.to.processing.error", 
                        file=file_path.name, 
                        error=str(e))
            return None

    def move_to_processed(self, file_path: Path) -> Optional[Path]:
        """Перемещение обработанного файла"""
        try:
            # Если файл в processing, берем его оттуда
            if not file_path.exists():
                processing_file = settings.PROCESSING_DIR / file_path.name
                if processing_file.exists():
                    file_path = processing_file
                else:
                    logger.warning("move.to.processed.file.not.exists", file=file_path.name)
                    return None
            
            destination = settings.PROCESSED_DIR / file_path.name
            shutil.move(str(file_path), str(destination))
            
            logger.info("file.moved.to.processed", 
                       file=file_path.name, 
                       destination=str(destination))
            return destination
            
        except Exception as e:
            logger.error("move.to.processed.error", 
                        file=file_path.name, 
                        error=str(e))
            return None

    def save_transcription_result(self, result: Dict[str, Any], file_path: Path) -> Optional[Path]:
        """Сохранение результата транскрипции в JSON"""
        try:
            json_name = f"{file_path.stem}.json"
            json_path = settings.JSON_OUTPUT_DIR / json_name
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            logger.info("transcription.result.saved", file=file_path.name)
            return json_path
            
        except Exception as e:
            logger.error("save.transcription.result.failed", error=str(e))
            return None

    def cleanup_processing_dir(self) -> None:
        """Очистка папки с файлами в обработке"""
        try:
            for file_path in settings.PROCESSING_DIR.iterdir():
                if file_path.is_file():
                    file_path.unlink()
            logger.info("processing.dir.cleaned")
        except Exception as e:
            logger.error("cleanup.processing.dir.error", error=str(e))

    def get_processing_files(self) -> List[Path]:
        """Получить список файлов в обработке"""
        try:
            files = [
                file_path 
                for file_path in settings.PROCESSING_DIR.iterdir()
                if file_path.is_file() 
                and file_path.suffix.lower() in settings.SUPPORTED_AUDIO_FORMATS
            ]
            return files
        except Exception as e:
            logger.error("get.processing.files.error", error=str(e))
            return []