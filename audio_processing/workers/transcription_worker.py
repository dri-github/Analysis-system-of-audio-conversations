# workers/transcription_worker.py
import os
import aiohttp
import asyncio
import json
import time
from typing import Optional, Dict, Any, List
from pathlib import Path
from config import Config
from logging_config import get_component_logger

logger = get_component_logger("transcription_worker")

class AsyncTranscriptionWorker:
    def __init__(self):
        self.max_retries = Config.MAX_RETRIES
        self.max_concurrent = Config.MAX_CONCURRENT_TRANSCRIPTIONS
        self.transcription_service_url = Config.TRANSCRIPTION_SERVICE_URL
        self.autorization_service_url = Config.AUTORIZATION_SERVICE_URL
        self.api_endpoint_url = Config.API_ENDPOINT
        self.access_token = Config.TRANSCRIPTION_ACCESS_TOKEN
        self.login = Config.LOGIN
        self.password = Config.PASSWORD
        # НЕ создаем семафор здесь - создадим его в каждом потоке

    async def _get_x_access_token(self) -> str:
        """Асинхронная авторизация"""
        try:
            data = {
                'username': self.login,
                'password': self.password
            }
            
            headers = {
                'accept': 'application/json',
                'Content-Type': 'application/x-www-form-urlencoded'
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.autorization_service_url,
                    data=data,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=Config.TRANSCRIPTION_TIMEOUT)
                ) as response:
                    
                    if response.status == 200:
                        response_body = await response.json()
                        access_token = response_body.get("x-access-token")
                        if access_token:
                            logger.info("authorization_successful", token_prefix=access_token[:10] + "...")
                            self.access_token = access_token
                            return access_token
                        else:
                            raise ValueError("x-access-token not found")
                    else:
                        text = await response.text()
                        logger.error("authorization_failed", status_code=response.status, response_text=text[:200])
                        response.raise_for_status()
                        
        except Exception as e:
            logger.error("authorization_error", error=str(e), error_type=type(e).__name__)
            raise

    async def process_audio_files(self, file_paths: List[str], semaphore: asyncio.Semaphore) -> List[bool]:
        """Асинхронная обработка нескольких файлов с переданным семафором"""
        tasks = [self.process_audio_file(file_path, semaphore) for file_path in file_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Обрабатываем исключения
        final_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error("async_processing_error", error=str(result))
                final_results.append(False)
            else:
                final_results.append(result)
                
        return final_results

    async def process_audio_file(self, file_path: str, semaphore: asyncio.Semaphore) -> bool:
        """Асинхронная обработка одного файла с переданным семафором"""
        try:
            if not self._validate_file(file_path):
                logger.error("file_validation_failed", file_path=file_path)
                return False
            
            # Используем переданный семафор
            async with semaphore:
                transcription_result = await self._call_transcription_service(file_path)
            
            if not transcription_result:
                logger.error("transcription_failed", file_path=file_path)
                return False
            
            # Синхронные операции (файловая система)
            json_file_path = self._move_to_processed(transcription_result, file_path)
            
            # Асинхронная отправка на API
            if json_file_path:
                await self._send_to_api(transcription_result, json_file_path)
            
            logger.info("file_processing_completed", file_path=file_path, status="success")
            return True
            
        except Exception as e:
            logger.error("file_processing_error", file_path=file_path, error=str(e))
            return False

    def _validate_file(self, file_path: str) -> bool:
        # Синхронная проверка файла
        if not os.path.exists(file_path):
            logger.warning("file_not_exists", file_path=file_path)
            return False
        
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            logger.error("file_empty", file_path=file_path, file_size=file_size)
            return False
        
        return True

    async def _call_transcription_service(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Асинхронный вызов сервиса транскрипции с повторными попытками"""
        for attempt in range(self.max_retries):
            try:
                logger.debug("transcription_service_call_attempt", file_path=file_path, attempt=attempt + 1)
                return await self._real_transcription_service(file_path)
                
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.warning("transcription_service_attempt_failed", file_path=file_path, attempt=attempt + 1, error=str(e))
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)

    async def _real_transcription_service(self, file_path: str) -> Dict[str, Any]:
        """Асинхронный запрос к сервису транскрипции"""
        params = {
            'speakers': 0, 'speaker_counter': 0, 'async': 0, 'punctuation': 0,
            'normalization': 0, 'toxicity': 0, 'emotion': 0, 'voice_analyzer': 0,
            'vad': 'webrtc',
            'classifiers': '{"smc":{"Оценка_разговора_1":{"correction":1,"confidenceThreshold":40}},"see":{"FIO":{"correction":1,"confidenceThreshold":40}}}'
        }
        
        headers = {
            'accept': 'application/json',
            'x-access-token': self.access_token
        }
        
        # Читаем файл в памяти
        with open(file_path, 'rb') as audio_file:
            file_data = audio_file.read()
        
        filename = os.path.basename(file_path)
        
        # Создаем FormData для асинхронной отправки
        data = aiohttp.FormData()
        data.add_field('wav', file_data, filename=filename, content_type=f'audio/{self._get_file_extension(file_path)}')
        
        # Добавляем параметры
        for key, value in params.items():
            data.add_field(key, str(value))
        
        logger.info("transcription_request_sending", file_path=file_path)
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.transcription_service_url,
                data=data,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=Config.TRANSCRIPTION_TIMEOUT)
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    logger.info("transcription_successful", file_path=file_path)
                    return result
                else:
                    text = await response.text()
                    logger.error("transcription_api_error", file_path=file_path, status_code=response.status)
                    raise aiohttp.ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status,
                        message=text[:200]
                    )

    async def _send_to_api(self, json_body: Dict[str, Any], file_path: str) -> bool:
        """Асинхронная отправка на API"""
        for attempt in range(Config.API_MAX_RETRIES):
            try:
                filename = os.path.basename(file_path)
                normalized_path = file_path.replace('\\', '/')
                
                params = {'file_name': filename, 'fpath': normalized_path}
                
                logger.info("api_send_attempt", file_path=file_path, attempt=attempt + 1)
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.api_endpoint_url,
                        params=params,
                        json=json_body,
                        timeout=aiohttp.ClientTimeout(total=Config.API_TIMEOUT)
                    ) as response:
                        
                        if response.status == 200:
                            logger.info("api_send_successful", file_path=file_path)
                            return True
                        else:
                            text = await response.text()
                            logger.warning("api_send_failed", file_path=file_path, status_code=response.status)
                            if attempt == Config.API_MAX_RETRIES - 1:
                                return False
                            await asyncio.sleep(2 ** attempt)
                            
            except Exception as e:
                logger.warning("api_send_error", file_path=file_path, attempt=attempt + 1, error=str(e))
                if attempt == Config.API_MAX_RETRIES - 1:
                    return False
                await asyncio.sleep(2 ** attempt)
        
        return False

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
        try:
            filename = os.path.basename(file_path)
            destination = os.path.join(Config.PROCESSED_FOLDER, filename)
            
            os.rename(file_path, destination)
            
            json_filename = os.path.splitext(filename)[0]
            json_file_path = self.create_json_file(
                data=json_body,
                folder_path=Config.JSON_FOLDER,
                filename=json_filename
            )
            
            if json_file_path:
                logger.info("json_file_created_successfully", file_path=file_path, json_path=json_file_path)
            else:
                logger.error("json_file_creation_failed", file_path=file_path)
                
            logger.info("file_moved_to_processed", original_path=file_path, destination_path=destination)
            
            return json_file_path
            
        except Exception as e:
            logger.error("file_processing_cleanup_error", file_path=file_path, error=str(e))
            return file_path

    def create_json_file(
        self,
        data: Dict[str, Any],
        folder_path: str,
        filename: str,
        ensure_ascii: bool = False,
        indent: int = 2
    ) -> Optional[str]:
        try:
            Path(folder_path).mkdir(parents=True, exist_ok=True)
            
            if not filename.endswith('.json'):
                filename += '.json'
            
            file_path = Path(folder_path) / filename
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=ensure_ascii, indent=indent)
            
            return str(file_path)
            
        except Exception as e:
            logger.error("json_file_creation_error", folder_path=folder_path, filename=filename, error=str(e))
            return None

# Глобальный экземпляр
transcription_worker = AsyncTranscriptionWorker()

async def process_audio_files(file_paths: List[str], semaphore: asyncio.Semaphore) -> List[bool]:
    return await transcription_worker.process_audio_files(file_paths, semaphore)

async def process_audio_file(file_path: str, semaphore: asyncio.Semaphore) -> bool:
    return await transcription_worker.process_audio_file(file_path, semaphore)