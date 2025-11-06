"""
src/core/application.py - ПОЛНАЯ ВЕРСИЯ

Включает:
- ✅ MinIO интеграция
- ✅ Метрики (MetricsCollector)
- ✅ Конфигурация (управление в реальном времени)
- ✅ API Client (правильная отправка на API)
"""

import asyncio
from typing import Optional
from datetime import datetime

import structlog
from config.settings import settings
from src.core.exceptions import ApplicationError
from src.storage.storage_manager import StorageManager
from src.services.file_manager import FileManager
from src.monitoring.watcher import Watcher
from src.monitoring.metrics import MetricsCollector
from src.services.task_pool import TaskPool
from src.services.transcription_service import TranscriptionService
from src.services.api_client import APIClient

logger = structlog.get_logger()


class AudioProcessingApplication:
    """Главное приложение для обработки аудиофайлов с полной поддержкой MetricsCollector и конфигурации"""

    def __init__(self):
        """Инициализация приложения"""
        self.is_running = False
        self.is_paused = False

        # ✅ ИНИЦИАЛИЗИРУЕМ METRICS НАПРЯМУЮ (БЕЗ ОБЕРТКИ)
        self.metrics = MetricsCollector()
        logger.info("metrics.collector.initialized")

        # Инициализируем компоненты
        try:
            # 1. StorageManager (MinIO или локальная файловая система)
            self.storage_manager = StorageManager()
            logger.debug("storage_manager.created")

            # 2. FileManager
            self.file_manager = FileManager(self.storage_manager)
            logger.debug("file_manager.created")

            # 3. Сервисы
            self.transcription_service = TranscriptionService()
            self.api_client = APIClient()
            logger.debug("services.created")

            # 4. TaskPool с передачей metrics
            self.task_pool = TaskPool(
                transcription_service=self.transcription_service,
                api_client=self.api_client,
                file_manager=self.file_manager,
                metrics=self.metrics,
                max_concurrent_tasks=settings.MAX_CONCURRENT_TASKS,
                max_transcription_calls=settings.MAX_TRANSCRIPTION_CALLS,
                max_api_calls=settings.MAX_API_CALLS,
                queue_max_size=settings.TASK_QUEUE_MAX_SIZE
            )
            logger.debug("task_pool.created")

            # 5. Watcher
            self.watcher = Watcher(
                file_manager=self.file_manager,
                task_pool=self.task_pool,
                scan_interval=settings.QUEUE_CHECK_INTERVAL
            )
            logger.debug("watcher.created")

        except Exception as e:
            logger.error("application.initialization.failed", error=str(e))
            raise ApplicationError(f"Failed to initialize application: {e}")

    async def start(self) -> None:
        """Запуск приложения"""
        if self.is_running:
            logger.warning("application.already.running")
            return

        logger.info("application.starting")

        try:
            # 1. StorageManager
            await self.storage_manager.start()
            logger.info("storage_manager.started")

            # 2. Инициализируем MinIO buckets если используется
            if settings.USE_MINIO:
                await self.file_manager.initialize_minio_buckets()
                logger.info("minio.buckets.initialized", using_minio=True)
            else:
                logger.info("using.local.storage")

            # 3. Сервисы
            await self.transcription_service.start()
            logger.info("transcription_service.started")

            await self.api_client.start()
            logger.info("api_client.started")

            # 4. TaskPool
            await self.task_pool.start()
            logger.info("task_pool.started")

            # 5. Восстанавливаем файлы из processing
            await self.watcher.recover_processing_files()
            logger.info("processing.files.recovered")

            # 6. Watcher
            await self.watcher.start()
            logger.info("watcher.started")

            self.is_running = True
            self.is_paused = False

            logger.info("application.start.successful")

        except Exception as e:
            logger.error("application.start.failed", error=str(e))
            await self._cleanup()
            raise ApplicationError(f"Failed to start application: {e}")

    async def stop(self) -> None:
        """Остановка приложения"""
        if not self.is_running:
            logger.warning("application.not.running")
            return

        logger.info("application.stopping")
        self.is_running = False

        try:
            await self._cleanup()
            logger.info("application.stop.successful")
        except Exception as e:
            logger.error("application.stop.failed", error=str(e))

    async def _cleanup(self) -> None:
        """Очистка ресурсов"""
        try:
            if self.watcher and self.watcher.is_running:
                await self.watcher.stop()
                logger.debug("watcher.stopped")

            if self.task_pool and self.task_pool.is_running:
                await self.task_pool.stop()
                logger.debug("task_pool.stopped")

            if self.api_client:
                await self.api_client.stop()
                logger.debug("api_client.stopped")

            if self.transcription_service:
                await self.transcription_service.stop()
                logger.debug("transcription_service.stopped")

            if self.storage_manager:
                await self.storage_manager.stop()
                logger.debug("storage_manager.stopped")

            logger.debug("cleanup.complete")
        except Exception as e:
            logger.error("cleanup.error", error=str(e))

    async def pause(self) -> None:
        """Приостановка обработки"""
        if self.is_paused:
            logger.warning("application.already.paused")
            return

        logger.info("application.pausing")

        try:
            await self.watcher.pause()
            await self.task_pool.pause()
            self.is_paused = True
            logger.info("application.paused")
        except Exception as e:
            logger.error("application.pause.failed", error=str(e))

    async def resume(self) -> None:
        """Возобновление обработки"""
        if not self.is_paused:
            logger.warning("application.not.paused")
            return

        logger.info("application.resuming")

        try:
            await self.watcher.resume()
            await self.task_pool.resume()
            self.is_paused = False
            logger.info("application.resumed")
        except Exception as e:
            logger.error("application.resume.failed", error=str(e))

    async def restart(self) -> None:
        """Полный перезапуск приложения"""
        logger.info("application.restart.starting")
        
        try:
            if self.is_running:
                await self.stop()
                await asyncio.sleep(1)
            
            await self.start()
            logger.info("application.restart.success")
        except Exception as e:
            logger.error("application.restart.failed", error=str(e))
            raise ApplicationError(f"Failed to restart application: {e}")

    def get_status(self) -> dict:
        """Получение статуса приложения"""
        try:
            watcher_status = self.watcher.get_status() if hasattr(self.watcher, 'get_status') else {}
        except:
            watcher_status = {}

        try:
            task_pool_status = self.task_pool.get_status() if hasattr(self.task_pool, 'get_status') else {}
        except:
            task_pool_status = {}

        total_processed = task_pool_status.get('processed', 0)
        total_failed = task_pool_status.get('failed', 0)
        total = total_processed + total_failed
        success_rate = (total_processed / total * 100) if total > 0 else 0

        return {
            "is_running": self.is_running,
            "is_paused": self.is_paused,
            "storage_type": "minio" if settings.USE_MINIO else "local",
            "storage_enabled": settings.USE_MINIO,
            "watcher_status": watcher_status,
            "task_pool_status": {
                **task_pool_status,
                "success_rate": f"{success_rate:.1f}%",
                "queue_max_size": settings.TASK_QUEUE_MAX_SIZE
            },
            "timestamp": datetime.now().isoformat()
        }

    async def get_stats(self) -> dict:
        """Получение полной статистики"""
        stats = self.get_status()
        
        if self.task_pool and hasattr(self.task_pool, 'task_queue'):
            stats["queue_stats"] = {
                "current_size": self.task_pool.task_queue.qsize(),
                "max_size": self.task_pool.task_queue.maxsize,
                "processed_total": self.task_pool.processed_count,
                "failed_total": self.task_pool.failed_count,
                "queue_full_events": getattr(self.task_pool, 'queue_full_events', 0),
            }
        
        if self.watcher:
            processed_count = self.watcher.get_processed_count() if hasattr(self.watcher, 'get_processed_count') else 0
            stats["watcher_stats"] = {
                "processed_files": processed_count,
                "storage_type": "minio" if settings.USE_MINIO else "local",
            }

        return stats
    
    async def restart_task_pool(self) -> None:
        """Перезагрузить пул задач с обновленными параметрами"""
        try:
            logger.info("taskpool.restart.starting")
            
            # Остановить старый TaskPool
            if self.task_pool and self.task_pool.is_running:
                logger.info("taskpool.stopping")
                await self.task_pool.stop()
                await asyncio.sleep(1)
                logger.info("taskpool.stopped")
            
            # ✅ НОВОЕ: Восстановить файлы из processing bucket
            logger.info("watcher.recovery.starting")
            await self.watcher.recover_processing_files()
            logger.info("watcher.recovery.completed")
            
            # Создать новый TaskPool
            logger.info("taskpool.creating.new",
                    max_workers=settings.MAX_CONCURRENT_TASKS)
            
            self.task_pool = TaskPool(
                transcription_service=self.transcription_service,
                api_client=self.api_client,
                file_manager=self.file_manager,
                metrics=self.metrics,
                max_concurrent_tasks=settings.MAX_CONCURRENT_TASKS,
                max_transcription_calls=settings.MAX_TRANSCRIPTION_CALLS,
                max_api_calls=settings.MAX_API_CALLS,
                queue_max_size=settings.TASK_QUEUE_MAX_SIZE
            )
            
            # Запустить новый TaskPool
            if self.is_running:
                logger.info("taskpool.starting.new")
                await self.task_pool.start()
                logger.info("taskpool.restarted.successfully",
                        new_max_workers=settings.MAX_CONCURRENT_TASKS)
                
                # Обновить ссылку в Watcher
                await self.watcher.update_task_pool(self.task_pool)
                logger.info("watcher.updated.with.new.taskpool")
                
                # Очистить кэш обработанных файлов
                self.watcher.reset_processed_files()
                logger.info("watcher.processed_files.reset")
            
        except Exception as e:
            logger.error("taskpool.restart.failed", error=str(e))
            raise ApplicationError(f"Failed to restart task pool: {e}")

