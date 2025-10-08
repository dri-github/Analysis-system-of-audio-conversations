# workers/transcription_worker.py
import os
import requests
import time
import json
from typing import Optional, Dict, Any
from pathlib import Path
import structlog
from config import Config

# Инициализация логгера
logger = structlog.get_logger()

class TranscriptionWorker:
    def __init__(self):
        self.max_retries = Config.MAX_RETRIES
        self.transcription_service_url = Config.TRANSCRIPTION_SERVICE_URL
        self.autorization_service_url = Config.AUTORIZATION_SERVICE_URL
        self.access_token = Config.TRANSCRIPTION_ACCESS_TOKEN
        self.login = Config.LOGIN
        self.password = Config.PASSWORD

    def _get_x_access_token(self) -> str:
        """Реальный вызов API авторизации"""
        try:
            params = {
                'username': self.login,
                'password': self.password
            }
            
            headers = {
                'accept': 'application/json'
            }

            logger.debug(
                "authorization.request.sending",
                authorization_url=self.autorization_service_url,
                username=self.login
            )

            response = requests.post(
                self.autorization_service_url,
                params=params,
                headers=headers,
                timeout=Config.TRANSCRIPTION_TIMEOUT
            )
            
            if response.status_code == 200:
                response_body = response.json()
                access_token = response_body.get("x-access-token")
                if access_token:
                    logger.info(
                        "authorization.successful",
                        token_prefix=access_token[:10] + "...",
                        token_length=len(access_token)
                    )
                    self.access_token = access_token
                    return access_token
                else:
                    logger.error(
                        "authorization.token.missing",
                        response_body=response_body
                    )
                    raise ValueError("x-access-token not found in response body")
            else:
                logger.error(
                    "authorization.failed",
                    status_code=response.status_code,
                    response_text=response.text[:200]  # Логируем первые 200 символов
                )
                response.raise_for_status()
                
        except Exception as e:
            logger.error(
                "authorization.error",
                error=str(e),
                error_type=type(e).__name__
            )
            raise

    def process_audio_file(self, file_path: str) -> bool:
        """Основная функция обработки аудиофайла"""
        try:
            # 1. Валидация файла
            if not self._validate_file(file_path):
                logger.error("file.validation.failed", file_path=file_path)
                return False
            
            # 2. Вызов сервиса транскрипции
            transcription_result = self._call_transcription_service(file_path)
            if not transcription_result:
                logger.error("transcription.failed", file_path=file_path)
                return False
            
            # 3. Перемещение обработанного файла и создание JSON
            self._move_to_processed(transcription_result, file_path)
            
            logger.info(
                "file.processing.completed",
                file_path=file_path,
                status="success"
            )
            return True
            
        except Exception as e:
            logger.error(
                "file.processing.error",
                file_path=file_path,
                error=str(e),
                error_type=type(e).__name__
            )
            return False

    def _validate_file(self, file_path: str) -> bool:
        """Проверка существования и размера файла"""
        if not os.path.exists(file_path):
            logger.warning("file.not.exists", file_path=file_path)
            return False
        
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            logger.error("file.empty", file_path=file_path, file_size=file_size)
            return False
        
        logger.debug(
            "file.validation.passed",
            file_path=file_path,
            file_size=file_size,
            file_size_mb=round(file_size / (1024 * 1024), 2)
        )
        return True

    def _call_transcription_service(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Вызов реального сервиса транскрипции"""
        for attempt in range(self.max_retries):
            try:
                logger.debug(
                    "transcription.service.call.attempt",
                    file_path=file_path,
                    attempt=attempt + 1,
                    max_attempts=self.max_retries
                )
                return self._real_transcription_service(file_path)
                
            except requests.exceptions.RequestException as e:
                logger.warning(
                    "transcription.service.attempt.failed",
                    file_path=file_path,
                    attempt=attempt + 1,
                    error=str(e),
                    error_type=type(e).__name__,
                    token_prefix=self.access_token[:10] + "..." if self.access_token else "missing"
                )
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(2 ** attempt)  # Exponential backoff

    def _real_transcription_service(self, file_path: str) -> Dict[str, Any]:
        """Реальный вызов API транскрипции"""
        params = {
            'speakers': 0,
            'speaker_counter': 0,
            'async': 0,
            'punctuation': 0,
            'normalization': 0,
            'toxicity': 0,
            'emotion': 0,
            'voice_analyzer': 0,
            'vad': 'webrtc',
            'classifiers': '{"smc":{"Оценка_разговора_1":{"correction":1,"confidenceThreshold":40}},"see":{"FIO":{"correction":1,"confidenceThreshold":40}}}'
        }
        
        headers = {
            'accept': 'application/json',
            'x-access-token': self.access_token
        }
        
        with open(file_path, 'rb') as audio_file:
            files = {
                'wav': (
                    os.path.basename(file_path),
                    audio_file,
                    f'audio/{self._get_file_extension(file_path)}'
                )
            }
            
            logger.info(
                "transcription.request.sending",
                file_path=file_path,
                service_url=self.transcription_service_url
            )
            
            response = requests.post(
                self.transcription_service_url,
                params=params,
                headers=headers,
                files=files,
                timeout=Config.TRANSCRIPTION_TIMEOUT
            )
        
        if response.status_code == 200:
            logger.info(
                "transcription.successful",
                file_path=file_path,
                response_size=len(response.text),
                response_keys=list(response.json().keys()) if response.text else []
            )
            return response.json()
        else:
            logger.error(
                "transcription.api.error",
                file_path=file_path,
                status_code=response.status_code,
                response_text=response.text[:200]
            )
            response.raise_for_status()

    def _get_file_extension(self, file_path: str) -> str:
        """Определяет расширение файла для MIME type"""
        ext = os.path.splitext(file_path)[1].lower().lstrip('.')
        mime_map = {
            'mp3': 'mpeg',
            'wav': 'wav',
            'm4a': 'mp4',
            'flac': 'flac',
            'ogg': 'ogg'
        }
        return mime_map.get(ext, 'mpeg')

    def _send_to_backend(self, file_path: str, transcription_data: Dict) -> bool:
        """Отправка результата в бэкенд"""
        try:
            conversation_id = self._extract_conversation_id(file_path)
            
            payload = {
                "conversation_id": conversation_id,
                "file_path": file_path,
                "transcription": transcription_data,
                "status": "completed"
            }
            
            logger.debug(
                "backend.sync.sending",
                file_path=file_path,
                conversation_id=conversation_id,
                backend_url=Config.TRANSCRIPTION_ENDPOINT
            )
            
            response = requests.post(
                Config.TRANSCRIPTION_ENDPOINT,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(
                    "backend.sync.successful",
                    file_path=file_path,
                    conversation_id=conversation_id
                )
                return True
            else:
                logger.error(
                    "backend.api.error",
                    file_path=file_path,
                    status_code=response.status_code,
                    response_text=response.text[:200]
                )
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(
                "backend.sync.failed",
                file_path=file_path,
                error=str(e),
                error_type=type(e).__name__
            )
            return False
    
    def _extract_conversation_id(self, file_path: str) -> str:
        """Извлечение ID разговора из имени файла"""
        filename = os.path.basename(file_path)
        if '_' in filename:
            return filename.split('_')[1]
        return filename.split('.')[0]
    
    def _move_to_processed(self, json_body: Dict[str, Any], file_path: str):
        """Перемещение обработанного файла и создание JSON"""
        try:
            filename = os.path.basename(file_path)
            destination = os.path.join(Config.PROCESSED_FOLDER, filename)
            
            # Перемещаем файл
            os.rename(file_path, destination)
            
            # Создаем JSON файл
            json_filename = os.path.splitext(filename)[0]
            json_success = self.create_json_file(
                data=json_body,
                folder_path=Config.JSON_FOLDER,
                filename=json_filename
            )
            
            if json_success:
                logger.info(
                    "json.file.created.successfully",
                    file_path=file_path,
                    json_filename=json_filename + '.json'
                )
            else:
                logger.error(
                    "json.file.creation.failed",
                    file_path=file_path
                )
                
            logger.info(
                "file.moved.to.processed",
                original_path=file_path,
                destination_path=destination
            )
            
        except OSError as e:
            logger.error(
                "file.move.failed",
                file_path=file_path,
                error=str(e),
                error_type=type(e).__name__
            )
        except Exception as e:
            logger.error(
                "file.processing.cleanup.error",
                file_path=file_path,
                error=str(e),
                error_type=type(e).__name__
            )

    def create_json_file(
        self,
        data: Dict[str, Any],
        folder_path: str,
        filename: str,
        ensure_ascii: bool = False,
        indent: int = 2
    ) -> bool:
        """
        Создает JSON файл с указанными данными в заданной папке
        """
        try:
            if not isinstance(folder_path, str):
                logger.error(
                    "json.creation.invalid.folder.path",
                    folder_path_type=type(folder_path),
                    expected_type="str"
                )
                return False
            
            # Создаем папку если не существует
            Path(folder_path).mkdir(parents=True, exist_ok=True)
            
            # Добавляем расширение .json если нужно
            if not filename.endswith('.json'):
                filename += '.json'
            
            # Полный путь к файлу
            file_path = Path(folder_path) / filename
            
            # Сохраняем данные в JSON файл
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=ensure_ascii, indent=indent)
            
            logger.debug(
                "json.file.created",
                file_path=str(file_path),
                data_keys=list(data.keys()) if data else [],
                file_size=os.path.getsize(file_path)
            )
            return True
            
        except Exception as e:
            logger.error(
                "json.file.creation.error",
                folder_path=folder_path,
                filename=filename,
                error=str(e),
                error_type=type(e).__name__
            )
            return False