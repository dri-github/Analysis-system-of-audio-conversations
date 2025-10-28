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
    """Клиент для отправки данных на внешнее API"""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.timeout = aiohttp.ClientTimeout(total=settings.API_TIMEOUT)
        self.max_retries = settings.API_MAX_RETRIES

    async def start(self):
        """Инициализация клиента"""
        self.session = aiohttp.ClientSession()

    async def stop(self):
        """Остановка клиента"""
        if self.session:
            await self.session.close()

    async def send_transcription_result(self, json_body: Dict[str, Any], file_path: str) -> bool:
        """Асинхронная отправка на API с повторными попытками"""
        for attempt in range(self.max_retries):
            try:
                filename = os.path.basename(file_path)
                normalized_path = file_path.replace('\\', '/')
                
                params = {'file_name': filename, 'fpath': normalized_path}
                
                logger.info("api_send_attempt", file_path=file_path, attempt=attempt + 1)
                
                async with self.session.post(
                    settings.API_ENDPOINT,
                    params=params,
                    json=json_body,
                    timeout=self.timeout
                ) as response:
                    
                    if response.status == 200:
                        logger.info("api_send_successful", file_path=file_path)
                        return True
                    else:
                        text = await response.text()
                        logger.warning("api_send_failed", file_path=file_path, status_code=response.status)
                        if attempt == self.max_retries - 1:
                            return False
                        await asyncio.sleep(2 ** attempt)
                        
            except Exception as e:
                logger.warning("api_send_error", file_path=file_path, attempt=attempt + 1, error=str(e))
                if attempt == self.max_retries - 1:
                    return False
                await asyncio.sleep(2 ** attempt)
        
        return False

    async def validate_connection(self) -> bool:
        """Проверка соединения с API"""
        try:
            async with self.session.get(
                settings.BACKEND_API_BASE,
                timeout=self.timeout
            ) as response:
                return response.status == 200
        except Exception as e:
            logger.error("api.connection.validation.failed", error=str(e))
            return False