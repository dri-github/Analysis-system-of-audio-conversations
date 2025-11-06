import aiohttp
import asyncio
import os
from typing import Dict, Any, Optional

try:
    from config.settings import settings
except ImportError:
    from config.settings import settings

from src.core.exceptions import APIError
import structlog

logger = structlog.get_logger()


class APIClient:
    """Клиент для отправки данных на API согласно FastAPI схеме"""

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.timeout = aiohttp.ClientTimeout(total=settings.API_TIMEOUT)
        self.max_retries = settings.API_MAX_RETRIES

    async def start(self):
        """Инициализация клиента"""
        self.session = aiohttp.ClientSession()
        logger.info("api.client.started", endpoint=settings.API_ENDPOINT)

    async def stop(self):
        """Остановка клиента"""
        if self.session:
            await self.session.close()
            logger.info("api.client.stopped")

    async def send_transcription_result(
        self, 
        json_body: Dict[str, Any], 
        file_path: str
    ) -> bool:
        """
        Асинхронная отправка результата транскрипции на API.
        
        Endpoint: POST /api/conversations?fname={file_name}&fpath={file_path}
        
        Body (JSON в теле запроса):
        {
            "filename": "...",
            "job_id": "...",
            "transcription": "...",
            "timestamp": ...
        }
        
        Args:
            json_body: Словарь с результатом транскрипции (БЕЗ обёртки!)
            file_path: Имя файла (используется как fpath параметр)
            
        Returns:
            bool: True если успешно (status 200 и получен id), False иначе
        """
        if not self.session:
            logger.error("api.client.not.initialized")
            return False

        # Получаем имя файла из пути
        file_name = os.path.basename(file_path)
        
        # ✅ ВАЖНО: json_body передаём БЕЗ обёртки в file_data
        
        logger.info(
            "api.send.preparing",
            endpoint=settings.API_ENDPOINT,
            file_name=file_name,
            file_path=file_path
        )

        for attempt in range(self.max_retries):
            try:
                # Формируем query параметры согласно требованию API
                params = {
                    "fname": file_name,  # Имя файла для query string
                    "fpath": file_path   # Путь файла для query string
                }
                
                logger.debug(
                    "api.send.attempt",
                    attempt=attempt + 1,
                    max_retries=self.max_retries,
                    file_name=file_name,
                    url_params=params
                )

                # ✅ Отправляем JSON тело БЕЗ обёртки
                # json_body = {
                #     "filename": "...",
                #     "job_id": "...",
                #     "transcription": "...",
                #     "timestamp": ...
                # }
                
                async with self.session.post(
                    settings.API_ENDPOINT,
                    params=params,           # fname и fpath в query string
                    json=json_body,          # ✅ JSON в теле БЕЗ обёртки
                    timeout=self.timeout,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    
                    response_text = await response.text()
                    
                    if response.status == 200:
                        # Парсим ответ для получения id
                        try:
                            response_data = await response.json()
                            conversation_id = response_data.get("id")
                            
                            logger.info(
                                "api.send.success",
                                file=file_name,
                                attempt=attempt + 1,
                                status=response.status,
                                conversation_id=conversation_id
                            )
                            return True
                        except Exception as parse_error:
                            logger.error(
                                "api.send.response.parse.error",
                                file=file_name,
                                error=str(parse_error),
                                response=response_text
                            )
                            return False
                    
                    elif response.status == 422:
                        # Ошибка валидации FastAPI
                        logger.error(
                            "api.send.validation.error",
                            file=file_name,
                            status=response.status,
                            error=response_text,
                            attempt=attempt + 1,
                            note="Check that json_body is valid and params are correct"
                        )
                        return False
                    
                    elif response.status == 400:
                        # Клиентская ошибка - не повторяем
                        logger.error(
                            "api.send.client.error",
                            file=file_name,
                            status=response.status,
                            error=response_text,
                            attempt=attempt + 1
                        )
                        return False
                    
                    elif response.status == 401 or response.status == 403:
                        # Ошибка аутентификации - не повторяем
                        logger.error(
                            "api.send.auth.error",
                            file=file_name,
                            status=response.status,
                            attempt=attempt + 1
                        )
                        return False
                    
                    elif response.status >= 500:
                        # Ошибка сервера - повторяем
                        logger.warning(
                            "api.send.server.error",
                            file=file_name,
                            status=response.status,
                            error=response_text,
                            attempt=attempt + 1
                        )
                        
                        # Если последняя попытка
                        if attempt == self.max_retries - 1:
                            logger.error(
                                "api.send.max.retries.exceeded",
                                file=file_name,
                                max_retries=self.max_retries,
                                status=response.status
                            )
                            return False
                        
                        # Ждём перед следующей попыткой (экспоненциальная задержка)
                        wait_time = 2 ** attempt
                        logger.debug(
                            "api.send.waiting.before.retry",
                            file=file_name,
                            wait_seconds=wait_time
                        )
                        await asyncio.sleep(wait_time)
                        continue
                    
                    else:
                        # Неожиданный статус код
                        logger.error(
                            "api.send.unexpected.status",
                            file=file_name,
                            status=response.status,
                            error=response_text,
                            attempt=attempt + 1
                        )
                        return False

            except asyncio.TimeoutError:
                logger.warning(
                    "api.send.timeout",
                    file=file_name,
                    attempt=attempt + 1,
                    timeout=settings.API_TIMEOUT
                )
                
                if attempt == self.max_retries - 1:
                    logger.error(
                        "api.send.timeout.max.retries",
                        file=file_name,
                        max_retries=self.max_retries,
                        timeout=settings.API_TIMEOUT
                    )
                    return False
                
                wait_time = 2 ** attempt
                await asyncio.sleep(wait_time)
                continue

            except aiohttp.ClientError as e:
                logger.warning(
                    "api.send.connection.error",
                    file=file_name,
                    error=str(e),
                    attempt=attempt + 1
                )
                
                if attempt == self.max_retries - 1:
                    logger.error(
                        "api.send.connection.failed.max.retries",
                        file=file_name,
                        max_retries=self.max_retries,
                        error=str(e)
                    )
                    return False
                
                wait_time = 2 ** attempt
                await asyncio.sleep(wait_time)
                continue

            except Exception as e:
                logger.error(
                    "api.send.unexpected.error",
                    file=file_name,
                    error=str(e),
                    error_type=type(e).__name__,
                    attempt=attempt + 1
                )
                return False

        logger.error(
            "api.send.all.attempts.failed",
            file=file_name,
            max_retries=self.max_retries
        )
        return False