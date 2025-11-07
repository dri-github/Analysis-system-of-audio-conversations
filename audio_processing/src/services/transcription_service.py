import aiohttp
import asyncio
import json
import os
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime



try:
    from config.settings import settings
except ImportError:
    from config.settings import settings



from src.core.exceptions import TranscriptionError
import structlog



logger = structlog.get_logger()



class TranscriptionService:
    """Сервис для работы с API транскрипции с поддержкой асинхронной обработки"""
    
    def __init__(self):
        self.auth_token: Optional[str] = settings.TRANSCRIPTION_ACCESS_TOKEN
        self.session: Optional[aiohttp.ClientSession] = None
        self.max_retries = settings.API_MAX_RETRIES
        
        # ✅ ФЛАГ АВТОРИЗАЦИИ
        self.use_authorization = getattr(settings, 'USE_AUTHORIZATION', False)
        
        # ✅ ОПТИМИЗИРОВАННЫЕ ТАЙМАУТЫ
        self.auth_timeout = aiohttp.ClientTimeout(total=60.0)
        self.timeout = aiohttp.ClientTimeout(total=settings.TRANSCRIPTION_TIMEOUT)
        
        # Параметры для асинхронной обработки
        self.polling_interval = 2.0
        self.max_polling_attempts = 300
        
        # Параметры авторизации
        self.auth_max_retries = 5
        self.auth_retry_delay = 5.0
        
        logger.info("transcription.service.configured",
                   use_authorization=self.use_authorization)



    async def start(self):
        """Инициализация сервиса - авторизация опциональна"""
        self.session = aiohttp.ClientSession()
        
        logger.info("transcription.service.starting",
                   mode="with_auth" if self.use_authorization else "no_auth")
        
        # ✅ АВТОРИЗАЦИЯ ТОЛЬКО ЕСЛИ ВКЛЮЧЕНА
        if self.use_authorization:
            if not self.auth_token and settings.LOGIN and settings.PASSWORD:
                try:
                    logger.info("transcription.service.attempting_authentication_on_startup")
                    await self._authenticate(retry=True)
                    logger.info("transcription.service.authenticated_on_startup")
                except Exception as e:
                    logger.warning("transcription.service.auth_failed_on_startup",
                                  error=str(e),
                                  error_type=type(e).__name__,
                                  message="Will retry authentication on first transcription request")
        else:
            logger.info("transcription.service.auth_disabled")



    async def stop(self):
        """Остановка сервиса"""
        if self.session:
            await self.session.close()
            logger.info("transcription.service.stopped")



    async def _authenticate(self, retry: bool = True) -> str:
        """
        Асинхронная авторизация в сервисе транскрипции.
        
        Пропускается если USE_AUTHORIZATION=False
        """
        # ✅ ВЫХОД ЕСЛИ АВТОРИЗАЦИЯ ОТКЛЮЧЕНА
        if not self.use_authorization:
            logger.info("transcription.auth.skipped_auth_disabled")
            return None
        
        max_retries = self.auth_max_retries if retry else 1
        
        logger.info("authentication.starting", max_retries=max_retries)
        
        for attempt in range(1, max_retries + 1):
            try:
                data = {
                    'username': settings.LOGIN,
                    'password': settings.PASSWORD
                }
                
                headers = {
                    'accept': 'application/json',
                    'Content-Type': 'application/x-www-form-urlencoded'
                }


                logger.info("authentication.attempt.sending",
                           attempt=attempt,
                           max_retries=max_retries,
                           timeout=self.auth_timeout.total)


                async with self.session.post(
                    settings.AUTHORIZATION_SERVICE_URL,
                    data=data,
                    headers=headers,
                    timeout=self.auth_timeout
                ) as response:
                    if response.status == 200:
                        response_body = await response.json()
                        access_token = response_body.get("x-access-token")
                        if access_token:
                            self.auth_token = access_token
                            logger.info("authentication.successful", 
                                       token_prefix=access_token[:10] + "...",
                                       attempt=attempt)
                            return access_token
                        else:
                            raise TranscriptionError("x-access-token not found in response")
                    else:
                        text = await response.text()
                        logger.error("authentication.failed", 
                                   status_code=response.status, 
                                   response_text=text[:200],
                                   attempt=attempt)
                        raise aiohttp.ClientResponseError(
                            request_info=response.request_info,
                            history=response.history,
                            status=response.status,
                            message=f"Authorization failed: {text[:200]}"
                        )
                        
            except asyncio.TimeoutError as e:
                logger.warning("authentication.timeout",
                              attempt=attempt,
                              max_retries=max_retries,
                              timeout=self.auth_timeout.total,
                              error=str(e))
                
                if attempt < max_retries:
                    delay = self.auth_retry_delay * (2 ** (attempt - 1))
                    delay = min(delay, 60.0)
                    
                    logger.info("authentication.retrying_after_timeout", 
                               attempt=attempt,
                               next_delay=delay)
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error("authentication.failed_after_timeout_retries",
                               max_retries=max_retries)
                    raise TranscriptionError(f"Authentication timeout after {max_retries} attempts: {e}")
            
            except aiohttp.ClientConnectorError as e:
                logger.warning("authentication.connection_error",
                              attempt=attempt,
                              max_retries=max_retries,
                              error=str(e))
                
                if attempt < max_retries:
                    delay = self.auth_retry_delay * (2 ** (attempt - 1))
                    delay = min(delay, 60.0)
                    
                    logger.info("authentication.retrying_after_connection_error", 
                               attempt=attempt,
                               next_delay=delay)
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error("authentication.failed_after_connection_error_retries",
                               max_retries=max_retries)
                    raise TranscriptionError(f"Connection error after {max_retries} attempts: {e}")
            
            except aiohttp.ClientResponseError as e:
                logger.error("authentication.response_error",
                           status=e.status,
                           attempt=attempt,
                           error=str(e))
                
                if attempt < max_retries and e.status >= 500:
                    delay = self.auth_retry_delay * attempt
                    delay = min(delay, 60.0)
                    
                    logger.info("authentication.retrying_after_server_error", 
                               attempt=attempt,
                               next_delay=delay,
                               status=e.status)
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise TranscriptionError(f"Authentication error: {e}")
                
            except Exception as e:
                logger.error("authentication.unexpected_error", 
                           error=str(e), 
                           error_type=type(e).__name__,
                           attempt=attempt)
                raise TranscriptionError(f"Authentication error: {e}")
        
        raise TranscriptionError(f"Authentication failed after {max_retries} attempts")



    # ============ АСИНХРОННАЯ ОБРАБОТКА ============


    async def submit_transcription_job(self, file_bytes: bytes, filename: str) -> Optional[str]:
        """
        Отправить файл аудио на транскрипцию.
        
        Args:
            file_bytes: Байты аудиофайла (напрямую из MinIO)
            filename: Имя файла (например, "audio.mp3")
        
        Returns:
            task_id: ID задачи транскрипции или None
        """
        task_id = None
        
        try:
            file_size_mb = len(file_bytes) / 1024 / 1024
            logger.info(
                "transcription.async_job.submitting",
                file=filename,
                file_size_mb=round(file_size_mb, 2)
            )
            
            # ✅ Аутентификация если нужна
            if self.use_authorization and not self.auth_token:
                logger.info("transcription.no_token_attempting_auth")
                await self.authenticate(retry=True)
            
            # ✅ Параметры для API
            params = {
                "speakers": "1",
                "speaker_counter": "0",
                "async": "1",
                "1": "1",
                "punctuation": "0",
                "normalization": "0",
                "toxicity": "1",
                "emotion": "1",
                "voice_analyzer": "1",
                "vad": "webrtc",
                "classifiers": '{"smc":{"Скрипты1":{"correction":1,"confidenceThreshold":40}},"see":{"FIO":{"correction":1,"confidenceThreshold":40}}}'
            }
            
            # ✅ Заголовки
            headers = {"accept": "application/json"}
            if self.use_authorization and self.auth_token:
                headers["x-access-token"] = self.auth_token
            
            # ✅ НОВОЕ: Формируем данные напрямую из file_bytes (БЕЗ ВРЕМЕННОГО ФАЙЛА!)
            data = aiohttp.FormData()
            
            # Добавляем байты файла напрямую
            data.add_field(
                "wav",
                file_bytes,
                filename=filename,
                content_type=f"audio/{self.get_file_extension(filename)}"
            )
            
            # Добавляем параметры
            for key, value in params.items():
                data.add_field(key, str(value))
            
            # ✅ POST запрос с байтами (не с файлом!)
            async with self.session.post(
                settings.TRANSCRIPTION_SERVICE_URL,
                data=data,
                headers=headers,
                timeout=self.timeout
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    
                    logger.debug(
                        "transcription.submit.raw_response",
                        job_response=result
                    )
                    
                    task_id = result.get("taskID")
                    if not task_id:
                        logger.error(
                            "transcription.async_job.no_id_in_response",
                            response=result
                        )
                        return None
                    
                    logger.info(
                        "transcription.async_job.submitted",
                        file=filename,
                        task_id=task_id,
                        file_size_mb=round(file_size_mb, 2)
                    )
                    
                    return task_id
                
                elif response.status == 401:
                    # Token истек
                    if self.use_authorization:
                        logger.warning(
                            "transcription.token.expired",
                            file=filename
                        )
                        self.auth_token = None
                        await self.authenticate(retry=True)
                        raise aiohttp.ClientResponseError(
                            request_info=response.request_info,
                            history=response.history,
                            status=response.status,
                            message="Token expired or authentication required"
                        )
                    else:
                        text = await response.text()
                        logger.error(
                            "transcription.async_job.api_error",
                            file=filename,
                            status_code=response.status,
                            response_text=text[:200]
                        )
                        raise aiohttp.ClientResponseError(
                            request_info=response.request_info,
                            history=response.history,
                            status=response.status,
                            message=text[:200]
                        )
                
                else:
                    text = await response.text()
                    logger.error(
                        "transcription.async_job.api_error",
                        file=filename,
                        status_code=response.status,
                        response_text=text[:200]
                    )
                    raise aiohttp.ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status,
                        message=text[:200]
                    )
        
        except Exception as e:
            logger.error(
                "transcription.async_job.submission.error",
                error=str(e),
                file=filename
            )
            return None


    def get_file_extension(self, filename: str) -> str:
        """
        Получить расширение файла для определения MIME type.
        
        Args:
            filename: Имя файла (например, "audio.mp3")
        
        Returns:
            Расширение без точки (например, "mpeg")
        """
        import os
        
        # Получить расширение файла
        _, ext = os.path.splitext(filename)
        ext = ext.lower().lstrip('.')  # Убрать точку и сделать нижний регистр
        
        # Маппинг расширений на MIME types
        mime_map = {
            'mp3': 'mpeg',
            'wav': 'wav',
            'm4a': 'mp4',
            'flac': 'flac',
            'ogg': 'ogg',
            'aac': 'aac',
        }
        
        # Вернуть соответствующий MIME type или исходное расширение
        return mime_map.get(ext, ext or 'mpeg')


    async def check_transcription_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Проверить статус обработки по taskID.
        
        Использует endpoint: GET /spr/result/{taskID}
        
        Статусы:
        - ready: готово (есть результат)
        - waiting: ожидание (еще обрабатывается)
        - not found: не найдена
        - failed: сбой
        
        Возвращает словарь с информацией о статусе.
        """
        try:
            logger.debug("transcription.status.checking", task_id=task_id)
            
            # ✅ АВТОРИЗАЦИЯ ТОЛЬКО ЕСЛИ НУЖНА
            if self.use_authorization and not self.auth_token:
                await self._authenticate(retry=True)
            
            # ✅ ЗАГОЛОВКИ БЕЗ ТОКЕНА, ЕСЛИ АВТОРИЗАЦИЯ ОТКЛЮЧЕНА
            headers = {
                'accept': 'application/json'
            }
            
            if self.use_authorization and self.auth_token:
                headers['x-access-token'] = self.auth_token
            
            # ✅ ПРАВИЛЬНЫЙ ENDPOINT для получения результата
            result_url = f"{settings.TRANSCRIPTION_SERVICE_BY_JOB_URL}/{task_id}"
            logger.debug("transcription.status.request_url", url=result_url)
            
            async with self.session.get(
                result_url,
                headers=headers,
                timeout=self.timeout
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    
                    # ✅ ЛОГИРУЕМ ПОЛНЫЙ ОТВЕТ
                    logger.debug("transcription.status.raw_response",
                                task_id=task_id,
                                status_response=result,
                                response_keys=list(result.keys()))
                    
                    # ✅ Парсим ответ с учетом поля status
                    status = result.get('status')
                    
                    # ✅ ЛОГИРУЕМ РАСПОЗНАННЫЙ СТАТУС
                    logger.info("transcription.status.parsed",
                               task_id=task_id,
                               parsed_status=status)
                    
                    # ✅ Обработка статусов согласно API документации
                    if status == 'ready':
                        # Результат готов!
                        logger.info("transcription.status.completed", task_id=task_id)
                        return {
                            'status': 'completed',
                            'result': result,
                            'api_status': status
                        }
                    elif status == 'waiting':
                        # Еще обрабатывается
                        logger.debug("transcription.status.processing", task_id=task_id)
                        return {
                            'status': 'processing',
                            'result': None,
                            'api_status': status
                        }
                    elif status == 'not found':
                        # Задача не найдена
                        logger.warning("transcription.status.not_found",
                                      task_id=task_id)
                        return {
                            'status': 'error',
                            'result': None,
                            'error': 'Task not found',
                            'api_status': status
                        }
                    elif status == 'failed':
                        # Сбой при обработке
                        error_msg = result.get('error') or 'Task processing failed'
                        logger.warning("transcription.status.failed",
                                      task_id=task_id,
                                      error=error_msg)
                        return {
                            'status': 'error',
                            'result': None,
                            'error': error_msg,
                            'api_status': status
                        }
                    else:
                        # Неизвестный статус
                        logger.warning("transcription.status.unknown",
                                      task_id=task_id,
                                      status=status)
                        return {
                            'status': 'unknown',
                            'result': result,
                            'api_status': status
                        }
                
                elif response.status == 401:
                    # ✅ ОБРАБОТКА 401 ТОЛЬКО ЕСЛИ АВТОРИЗАЦИЯ ВКЛЮЧЕНА
                    if self.use_authorization:
                        self.auth_token = None
                        await self._authenticate(retry=True)
                    
                    raise aiohttp.ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status,
                        message="Token expired or authentication required"
                    )
                else:
                    text = await response.text()
                    logger.warning("transcription.status.http_error",
                                  task_id=task_id,
                                  status=response.status,
                                  response_text=text[:200])
                    return {
                        'status': 'error',
                        'result': None,
                        'error': f'HTTP {response.status}',
                        'api_status': None
                    }


        except Exception as e:
            logger.error("transcription.status.error",
                        task_id=task_id,
                        error=str(e))
            return {
                'status': 'error',
                'result': None,
                'error': str(e),
                'api_status': None
            }



    async def poll_transcription_result(self, task_id: str, 
                                       max_attempts: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Проверять статус обработки пока результат не будет готов.
        
        Параметры:
        - task_id: ID задачи
        - max_attempts: максимум попыток (по умолчанию 300 = 10 минут)
        
        Возвращает результат транскрипции или None если ошибка/таймаут.
        """
        if max_attempts is None:
            max_attempts = self.max_polling_attempts
        
        logger.info("transcription.polling.starting",
                   task_id=task_id,
                   max_attempts=max_attempts,
                   polling_interval=self.polling_interval,
                   timeout_minutes=int((max_attempts * self.polling_interval) / 60))
        
        for attempt in range(1, max_attempts + 1):
            try:
                # ✅ ЛОГИРУЕМ НАЧАЛО ПОПЫТКИ
                logger.debug("transcription.polling.attempt_start",
                            task_id=task_id,
                            attempt=attempt,
                            max_attempts=max_attempts)
                
                status_info = await self.check_transcription_status(task_id)
                
                if not status_info:
                    logger.warning("transcription.polling.no_response",
                                  task_id=task_id,
                                  attempt=attempt)
                    await asyncio.sleep(self.polling_interval)
                    continue
                
                status = status_info.get('status')
                
                # ✅ ЛОГИРУЕМ ПОЛУЧЕННЫЙ СТАТУС
                logger.info("transcription.polling.status_received",
                           task_id=task_id,
                           attempt=attempt,
                           status=status,
                           api_status=status_info.get('api_status'))
                
                if status == 'completed':
                    logger.info("transcription.polling.completed",
                               task_id=task_id,
                               attempt=attempt,
                               total_seconds=int(attempt * self.polling_interval))
                    return status_info.get('result')
                
                elif status == 'error':
                    logger.error("transcription.polling.error",
                                task_id=task_id,
                                error=status_info.get('error'),
                                api_status=status_info.get('api_status'))
                    return None
                
                elif status == 'processing':
                    # ✅ УЛУЧШЕННОЕ ЛОГИРОВАНИЕ
                    if attempt % 5 == 0:
                        logger.info("transcription.polling.still_processing",
                                   task_id=task_id,
                                   attempt=attempt,
                                   elapsed_seconds=int(attempt * self.polling_interval))
                    else:
                        logger.debug("transcription.polling.processing_wait",
                                    task_id=task_id,
                                    attempt=attempt)
                    
                    if attempt < max_attempts:
                        logger.debug("transcription.polling.sleeping",
                                    task_id=task_id,
                                    sleep_seconds=self.polling_interval)
                        await asyncio.sleep(self.polling_interval)
                        continue
                    else:
                        logger.error("transcription.polling.timeout",
                                    task_id=task_id,
                                    max_attempts=max_attempts,
                                    timeout_seconds=int(max_attempts * self.polling_interval))
                        return None
                
                else:
                    # ⚠️ НЕИЗВЕСТНЫЙ СТАТУС
                    logger.warning("transcription.polling.unexpected_status",
                                  task_id=task_id,
                                  status=status,
                                  attempt=attempt,
                                  full_status_info=status_info)
                    
                    # Неизвестный статус - пробуем продолжить
                    if attempt < max_attempts:
                        await asyncio.sleep(self.polling_interval)
                        continue
                    else:
                        return None
            
            except Exception as e:
                logger.error("transcription.polling.iteration_error",
                            task_id=task_id,
                            attempt=attempt,
                            error=str(e))
                await asyncio.sleep(self.polling_interval)
        
        logger.error("transcription.polling.max_attempts_exceeded",
                    task_id=task_id,
                    total_seconds=int(max_attempts * self.polling_interval))
        return None



    # ============ СИНХРОННАЯ ОБРАБОТКА (СОВМЕСТИМОСТЬ) ============


    async def transcribe_audio(self, file_path: str) -> Dict[str, Any]:
        """
        Синхронная транскрипция (для совместимости).
        
        Внутренне использует асинхронный API:
        1. Отправляет файл на асинхронную обработку (получает taskID)
        2. Проверяет статус в цикле через GET /spr/result/{taskID}
        3. Возвращает результат
        """
        try:
            # ✅ Отправляем файл на асинхронную обработку
            task_id = await self.submit_transcription_job(file_path)
            
            if not task_id:
                logger.error("transcription.sync.submission_failed",
                            file_path=file_path)
                raise TranscriptionError("Failed to submit transcription job")
            
            logger.info("transcription.sync.job_submitted",
                       file=os.path.basename(file_path),
                       task_id=task_id)
            
            # ✅ Проверяем статус пока не будет готов
            result = await self.poll_transcription_result(task_id)
            
            if result:
                logger.info("transcription.sync.success",
                           file=os.path.basename(file_path),
                           task_id=task_id)
                return result
            else:
                logger.error("transcription.sync.failed",
                            file_path=file_path,
                            task_id=task_id)
                raise TranscriptionError(f"Transcription job {task_id} failed or timed out")
        
        except Exception as e:
            logger.error("transcription.sync.error",
                        file_path=file_path,
                        error=str(e))
            raise



    def _get_file_extension(self, file_path: str) -> str:
        """Определение MIME-типа по расширению файла"""
        ext = os.path.splitext(file_path)[1].lower().lstrip('.')
        mime_map = {
            'mp3': 'mpeg',
            'wav': 'wav',
            'm4a': 'mp4',
            'flac': 'flac',
            'ogg': 'ogg',
            'aac': 'aac'
        }
        return mime_map.get(ext, 'mpeg')



    async def validate_connection(self) -> bool:
        """Проверка соединения с сервисом транскрипции"""
        try:
            # ✅ ЕСЛИ АВТОРИЗАЦИЯ ОТКЛЮЧЕНА - ПРОСТО ВОЗВРАЩАЕМ TRUE
            if not self.use_authorization:
                logger.info("transcription.connection.validated_no_auth")
                return True
            
            # ИНАЧЕ - ПРОВЕРЯЕМ АВТОРИЗАЦИЮ
            if not self.auth_token and settings.LOGIN and settings.PASSWORD:
                await self._authenticate(retry=False)
                return True
            elif self.auth_token:
                return True
            else:
                logger.warning("transcription.service.no.credentials")
                return False
        except Exception as e:
            logger.error("connection.validation.failed", error=str(e))
            return False



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
            # Используем переданный семафор
            async with semaphore:
                transcription_result = await self.transcribe_audio(file_path)
            
            return transcription_result is not None
            
        except Exception as e:
            logger.error("file_processing_error", file_path=file_path, error=str(e))
            return False
