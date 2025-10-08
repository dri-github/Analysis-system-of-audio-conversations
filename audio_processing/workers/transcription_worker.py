# workers/transcription_worker.py
import os
import requests
import time
import json
from typing import Optional, Dict, Any
from pathlib import Path
from config import Config
from logging_config import get_component_logger

# Инициализация логгера
logger = get_component_logger("transcription_worker")

class TranscriptionWorker:
    def __init__(self):
        self.max_retries = Config.MAX_RETRIES
        self.api_max_retries = Config.API_MAX_RETRIES
        self.transcription_service_url = Config.TRANSCRIPTION_SERVICE_URL
        self.autorization_service_url = Config.AUTORIZATION_SERVICE_URL
        self.api_service_url = Config.BACKEND_API_BASE
        self.api_endpoint_url = Config.API_ENDPOINT
        self.access_token = Config.TRANSCRIPTION_ACCESS_TOKEN
        self.login = Config.LOGIN
        self.password = Config.PASSWORD

    def _get_x_access_token(self) -> str:
        """Реальный вызов API авторизации"""
        try:
            data = {
                'username': self.login,
                'password': self.password
            }
            
            headers = {
                'accept': 'application/json',
                'Content-Type': 'application/x-www-form-urlencoded'
            }

            logger.info(
                "authorization_request_sending",
                authorization_url=self.autorization_service_url
            )

            response = requests.post(
                self.autorization_service_url,
                data=data,
                headers=headers,
                timeout=Config.TRANSCRIPTION_TIMEOUT
            )
            
            if response.status_code == 200:
                response_body = response.json()
                access_token = response_body.get("x-access-token")
                if access_token:
                    logger.info(
                        "authorization_successful",
                        token_prefix=access_token[:10] + "..."
                    )
                    self.access_token = access_token
                    return access_token
                else:
                    logger.error(
                        "authorization_token_missing",
                        response_body=response_body
                    )
                    raise ValueError("x-access-token not found in response body")
            else:
                logger.error(
                    "authorization_failed",
                    status_code=response.status_code,
                    response_text=response.text[:200]
                )
                response.raise_for_status()
                
        except Exception as e:
            logger.error(
                "authorization_error",
                error=str(e),
                error_type=type(e).__name__
            )
            raise

    def process_audio_file(self, file_path: str) -> bool:
        """Основная функция обработки аудиофайла"""
        try:
            if not self._validate_file(file_path):
                logger.error("file_validation_failed", file_path=file_path)
                return False
            
            transcription_result = self._call_transcription_service(file_path)
            if not transcription_result:
                logger.error("transcription_failed", file_path=file_path)
                return False
            
            # Сохраняем JSON локально и отправляем на сервер
            final_file_path = self._move_to_processed(transcription_result, file_path)
            
            # Отправляем на API
            api_success = self._send_to_api(transcription_result, final_file_path)
            
            if api_success:
                logger.info(
                    "file_processing_completed",
                    file_path=file_path,
                    status="success",
                    api_sent=True
                )
            else:
                logger.warning(
                    "file_processing_completed_but_api_failed",
                    file_path=file_path,
                    status="partial_success",
                    api_sent=False
                )
            
            return True  # Возвращаем True даже если API не удалось, т.к. файл обработан
            
        except Exception as e:
            logger.error(
                "file_processing_error",
                file_path=file_path,
                error=str(e),
                error_type=type(e).__name__
            )
            return False

    def _validate_file(self, file_path: str) -> bool:
        if not os.path.exists(file_path):
            logger.warning("file_not_exists", file_path=file_path)
            return False
        
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            logger.error("file_empty", file_path=file_path, file_size=file_size)
            return False
        
        return True

    def _call_transcription_service(self, file_path: str) -> Optional[Dict[str, Any]]:
        for attempt in range(self.max_retries):
            try:
                logger.debug(
                    "transcription_service_call_attempt",
                    file_path=file_path,
                    attempt=attempt + 1
                )
                return self._real_transcription_service(file_path)
                
            except requests.exceptions.RequestException as e:
                logger.warning(
                    "transcription_service_attempt_failed",
                    file_path=file_path,
                    attempt=attempt + 1,
                    error=str(e)
                )
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(2 ** attempt)

    def _real_transcription_service(self, file_path: str) -> Dict[str, Any]:
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
                "transcription_request_sending",
                file_path=file_path
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
                "transcription_successful",
                file_path=file_path,
                response_keys=list(response.json().keys()) if response.text else []
            )
            return response.json()
        else:
            logger.error(
                "transcription_api_error",
                file_path=file_path,
                status_code=response.status_code,
                response_text=response.text[:200] if response.text else "empty response"
            )
            response.raise_for_status()

    def _get_file_extension(self, file_path: str) -> str:
        ext = os.path.splitext(file_path)[1].lower().lstrip('.')
        mime_map = {
            'mp3': 'mpeg',
            'wav': 'wav',
            'm4a': 'mp4',
            'flac': 'flac',
            'ogg': 'ogg'
        }
        return mime_map.get(ext, 'mpeg')
    
    def _move_to_processed(self, json_body: Dict[str, Any], file_path: str) -> str:
        """Перемещает файл и создает JSON, возвращает путь к JSON файлу"""
        try:
            filename = os.path.basename(file_path)
            destination = os.path.join(Config.PROCESSED_FOLDER, filename)
            
            # Перемещаем аудиофайл
            os.rename(file_path, destination)
            
            # Создаем JSON файл
            json_filename = os.path.splitext(filename)[0]
            json_file_path = self.create_json_file(
                data=json_body,
                folder_path=Config.JSON_FOLDER,
                filename=json_filename
            )
            
            if json_file_path:
                logger.info(
                    "json_file_created_successfully",
                    file_path=file_path,
                    json_path=json_file_path
                )
            else:
                logger.error(
                    "json_file_creation_failed",
                    file_path=file_path
                )
                return destination
                
            logger.info(
                "file_moved_to_processed",
                original_path=file_path,
                destination_path=destination,
                json_path=json_file_path
            )
            
            return json_file_path
            
        except Exception as e:
            logger.error(
                "file_processing_cleanup_error",
                file_path=file_path,
                error=str(e),
                error_type=type(e).__name__
            )
            return file_path  # Возвращаем оригинальный путь в случае ошибки

    def create_json_file(
        self,
        data: Dict[str, Any],
        folder_path: str,
        filename: str,
        ensure_ascii: bool = False,
        indent: int = 2
    ) -> Optional[str]:
        """Создает JSON файл и возвращает путь к нему"""
        try:
            Path(folder_path).mkdir(parents=True, exist_ok=True)
            
            if not filename.endswith('.json'):
                filename += '.json'
            
            file_path = Path(folder_path) / filename
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=ensure_ascii, indent=indent)
            
            logger.debug(
                "json_file_created",
                file_path=str(file_path),
                data_size=len(str(data))
            )
            return str(file_path)
            
        except Exception as e:
            logger.error(
                "json_file_creation_error",
                folder_path=folder_path,
                filename=filename,
                error=str(e),
                error_type=type(e).__name__
            )
            return None
    def _send_to_api(self, json_body: Dict[str, Any], file_path: str) -> bool:
        """Отправляет JSON данные на API с повторными попытками"""
        for attempt in range(self.api_max_retries):
            try:
                # НОРМАЛИЗУЕМ ПУТЬ - заменяем обратные слеши на прямые
                normalized_path = file_path.replace('\\', '/')
                filename = os.path.basename(normalized_path)
            
                logger.info(
                    "api_send_attempt",
                    file_path=normalized_path,
                    original_path=file_path,  # Логируем оригинальный путь для отладки
                    attempt=attempt + 1,
                    api_endpoint=self.api_endpoint_url
                )
            
                # Подготавливаем параметры с нормализованным путем
                params = {
                    'file_name': filename,
                    'fpath': normalized_path  # Используем нормализованный путь
                }
            
                # Отправляем запрос
                response = requests.post(
                    self.api_endpoint_url,
                    params=params,
                    json=json_body,
                    timeout=Config.API_TIMEOUT
                )
            
                if response.status_code == 200:
                    logger.info(
                        "api_send_successful",
                        file_path=normalized_path,
                        attempt=attempt + 1,
                        response_status=response.status_code
                    )
                    return True
                else:
                    logger.warning(
                        "api_send_failed",
                        file_path=normalized_path,
                        attempt=attempt + 1,
                        status_code=response.status_code,
                        response_text=response.text[:200] if response.text else "empty response"
                    )
                
                    if attempt == self.api_max_retries - 1:
                        logger.error(
                            "api_send_final_failure",
                            file_path=normalized_path,
                            total_attempts=self.api_max_retries
                        )
                        return False
                
                    time.sleep(2 ** attempt)
                
            except requests.exceptions.RequestException as e:
                logger.warning(
                    "api_send_network_error",
                    file_path=normalized_path,
                    attempt=attempt + 1,
                    error=str(e),
                    error_type=type(e).__name__
                )
            
                if attempt == self.api_max_retries - 1:
                    logger.error(
                        "api_send_network_final_failure",
                        file_path=normalized_path,
                        total_attempts=self.api_max_retries
                    )
                    return False
            
                time.sleep(2 ** attempt)
        
            except Exception as e:
                logger.error(
                    "api_send_unexpected_error",
                    file_path=normalized_path,
                    attempt=attempt + 1,
                    error=str(e),
                    error_type=type(e).__name__
                )
                return False
    
        return False
    
# Глобальный экземпляр для прямого вызова
transcription_worker = TranscriptionWorker()

def process_audio_file(file_path: str) -> bool:
    return transcription_worker.process_audio_file(file_path)