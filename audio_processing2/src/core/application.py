"""
Основное приложение для обработки аудио.
С поддержкой восстановления файлов из папки processing при запуске.
"""
import asyncio
from typing import Optional, Dict, Any
import structlog

from config.settings import settings
from src.core.exceptions import ApplicationError
from src.services.file_manager import FileManager
from src.services.transcription_service import TranscriptionService
from src.services.api_client import APIClient
from src.services.task_pool import TaskPool
from src.monitoring.watcher import Watcher
from src.monitoring.metrics import MetricsCollector

logger = structlog.get_logger()


class AudioProcessingApplication:
    """Основной класс приложения для обработки аудио"""
    
    def __init__(self):
        """Инициализация приложения"""
        self.is_running = False
        self.is_paused = False
        
        # Инициализация компонентов
        self.file_manager: Optional[FileManager] = None
        self.transcription_service: Optional[TranscriptionService] = None
        self.api_client: Optional[APIClient] = None
        self.task_pool: Optional[TaskPool] = None
        self.watcher: Optional[Watcher] = None
        self.metrics: Optional[MetricsCollector] = None

    async def start(self) -> None:
        """Запуск приложения"""
        if self.is_running:
            logger.warning("application.already.running")
            return

        try:
            logger.info("application.starting")
            
            # Инициализация компонентов
            self.file_manager = FileManager()
            self.transcription_service = TranscriptionService()
            self.api_client = APIClient()
            self.metrics = MetricsCollector()
            
            # Запуск сервисов
            await self.transcription_service.start()
            await self.api_client.start()
            
            # Проверка соединений
            if not await self.transcription_service.validate_connection():
                logger.warning("transcription.service.connection.failed")
            
            if not await self.api_client.validate_connection():
                logger.warning("api.client.connection.failed")
            
            # Инициализация пула задач
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
            
            # Инициализация мониторинга папок
            self.watcher = Watcher(
                file_manager=self.file_manager,
                task_pool=self.task_pool,
                scan_interval=settings.QUEUE_CHECK_INTERVAL
            )
            
            # Запуск компонентов
            await self.task_pool.start()
            await self.watcher.start()
            
            # ✅ НОВОЕ: Восстановить файлы из папки processing
            await self._recover_processing_files()
            
            self.is_running = True
            self.is_paused = False
            logger.info("application.started.successfully")
            
        except Exception as e:
            logger.error("application.start.failed", error=str(e))
            await self.stop()
            raise ApplicationError(f"Failed to start application: {e}")

    async def _recover_processing_files(self) -> None:
        """
        Восстановить файлы из папки processing.
        
        Если при предыдущем запуске приложение аварийно завершилось,
        в папке processing могут остаться незаконченные файлы.
        Эта функция добавляет их обратно в очередь обработки.
        """
        try:
            # Получаем список файлов в processing
            processing_files = self.file_manager.get_processing_files()
            
            if not processing_files:
                logger.info("recovery.no.files.found")
                return
            
            logger.warning("recovery.found.files", count=len(processing_files))
            
            # Добавляем каждый файл обратно в очередь обработки
            for file_path in processing_files:
                try:
                    await self.task_pool.add_task(file_path)
                    logger.info("recovery.file.added", file=file_path.name)
                except Exception as e:
                    logger.error("recovery.add.task.failed", 
                               file=file_path.name, 
                               error=str(e))
            
            logger.info("recovery.completed", files_recovered=len(processing_files))
            
        except Exception as e:
            logger.error("recovery.error", error=str(e))

    async def stop(self) -> None:
        """Остановка приложения"""
        if not self.is_running:
            return

        logger.info("application.stopping")
        
        try:
            # Останавливаем компоненты в правильном порядке
            if self.watcher:
                await self.watcher.stop()
                
            if self.task_pool:
                await self.task_pool.stop()
                
            if self.api_client:
                await self.api_client.stop()
                
            if self.transcription_service:
                await self.transcription_service.stop()
                
            self.is_running = False
            self.is_paused = False
            logger.info("application.stopped.successfully")
            
        except Exception as e:
            logger.error("application.stop.failed", error=str(e))
            raise

    async def pause(self) -> None:
        """Приостановка приложения"""
        if not self.is_running or self.is_paused:
            return

        logger.info("application.pausing")
        self.is_paused = True
        
        # Приостанавливаем компоненты
        if self.watcher:
            await self.watcher.pause()
            
        if self.task_pool:
            await self.task_pool.pause()
            
        logger.info("application.paused")

    async def resume(self) -> None:
        """Возобновление приложения"""
        if not self.is_running or not self.is_paused:
            return

        logger.info("application.resuming")
        self.is_paused = False
        
        # Возобновляем компоненты
        if self.task_pool:
            await self.task_pool.resume()
            
        if self.watcher:
            await self.watcher.resume()
            
        logger.info("application.resumed")

    async def restart(self) -> None:
        """Перезапуск приложения"""
        logger.info("application.restarting")
        await self.stop()
        await asyncio.sleep(1)
        await self.start()

    async def get_status(self) -> Dict[str, Any]:
        """Получение статуса приложения"""
        status = {
            "is_running": self.is_running,
            "is_paused": self.is_paused,
            "task_pool_status": await self.task_pool.get_status() if self.task_pool else {},
            "watcher_status": await self.watcher.get_status() if self.watcher else {},
            "metrics": await self.metrics.get_metrics() if self.metrics else {}
        }
        
        # Добавляем информацию о сервисах
        if self.transcription_service:
            status["transcription_service"] = {
                "has_token": bool(self.transcription_service.auth_token)
            }
            
        if self.api_client:
            status["api_client"] = {
                "is_connected": await self.api_client.validate_connection()
            }
            
        return status

    async def restart_task_pool(self) -> None:
        """
        Перезагрузить TaskPool с сохранением исторических метрик.
        """
        if not self.is_running:
            logger.warning("restart_task_pool.app.not.running")
            return
        
        try:
            logger.info("restart_task_pool.starting")
            
            # ✅ ШАГ 1: Сохранить метрики перед перезагрузкой
            if self.task_pool and self.metrics:
                logger.info("restart_task_pool.saving_metrics",
                        session_successful=self.task_pool.processed_count,
                        session_failed=self.task_pool.failed_count)
            
            # ШАГ 2: Останавливаем старый пул задач
            if self.task_pool:
                logger.info("restart_task_pool.stopping_old_pool")
                await self.task_pool.stop()
                logger.info("restart_task_pool.old.stopped")
            
            # ШАГ 3: Перемещаем файлы из processing обратно в upload
            logger.info("restart_task_pool.migrating_files")
            migrated_files = await self._migrate_processing_files()
            
            # Небольшая пауза для устойчивости
            logger.info("restart_task_pool.waiting")
            await asyncio.sleep(1.0)
            
            # ШАГ 4: Создаем новый пул с обновленными параметрами
            logger.info("restart_task_pool.creating_new_pool")
            from src.services.task_pool import TaskPool
            
            new_task_pool = TaskPool(
                transcription_service=self.transcription_service,
                api_client=self.api_client,
                file_manager=self.file_manager,
                metrics=self.metrics,  # ✅ Переиспользуем тот же MetricsCollector!
                max_concurrent_tasks=settings.MAX_CONCURRENT_TASKS,
                max_transcription_calls=settings.MAX_TRANSCRIPTION_CALLS,
                max_api_calls=settings.MAX_API_CALLS,
                queue_max_size=settings.TASK_QUEUE_MAX_SIZE
            )
            
            self.task_pool = new_task_pool
            logger.info("restart_task_pool.new_pool_created", 
                    new_pool_id=id(self.task_pool))
            
            # ✅ НОВОЕ: Сброс метрик текущей сессии (но история сохранена!)
            logger.info("restart_task_pool.resetting_session_metrics")
            self.metrics.reset_session_metrics()
            
            # ШАГ 5: Запускаем новый пул
            logger.info("restart_task_pool.starting_new_pool")
            await self.task_pool.start()
            logger.info("restart_task_pool.new.started",
                    max_concurrent_tasks=settings.MAX_CONCURRENT_TASKS,
                    new_pool_id=id(self.task_pool))
            
            # ШАГ 6: Обновляем ссылку в Watcher на новый пул
            logger.info("restart_task_pool.updating_watcher")
            if self.watcher:
                old_pool_id = id(self.watcher.task_pool)
                
                if hasattr(self.watcher, 'update_task_pool'):
                    await self.watcher.update_task_pool(self.task_pool)
                    logger.info("restart_task_pool.watcher.updated_async",
                            old_pool_id=old_pool_id,
                            new_pool_id=id(self.task_pool))
                else:
                    self.watcher.task_pool = self.task_pool
                    logger.info("restart_task_pool.watcher.updated_sync",
                            old_pool_id=old_pool_id,
                            new_pool_id=id(self.task_pool))
            else:
                logger.warning("restart_task_pool.watcher.not_found")
            
            # ШАГ 7: Принудительно добавляем мигрированные файлы в очередь
            logger.info("restart_task_pool.queueing_migrated_files",
                    count=len(migrated_files))
            
            for file_path in migrated_files:
                try:
                    await self.task_pool.add_task(file_path)
                    logger.info("restart_task_pool.migrated_file_queued",
                            file=file_path.name)
                except Exception as e:
                    logger.error("restart_task_pool.queue_migrated_file.failed",
                            file=file_path.name,
                            error=str(e))
            
            logger.info("restart_task_pool.completed_successfully",
                    migrated_files_count=len(migrated_files))
            
        except Exception as e:
            logger.error("restart_task_pool.failed", error=str(e))
            raise ApplicationError(f"Failed to restart task pool: {e}")

    async def _migrate_processing_files(self) -> list:
        """
        Перемещить все файлы из папки processing обратно в audio_uploads.
        
        Возвращает список перемещённых файлов для дальнейшей обработки.
        
        Это необходимо при перезагрузке TaskPool, чтобы:
        1. Файлы не потерялись
        2. Они были переобработаны с новыми параметрами конфигурации
        3. Очередь была очищена для нового начала
        """
        migrated_files = []
        
        try:
            processing_files = self.file_manager.get_processing_files()
            
            if not processing_files:
                logger.info("migrate_processing.no_files")
                return migrated_files
            
            logger.warning("migrate_processing.starting", count=len(processing_files))
            
            migrated_count = 0
            failed_count = 0
            
            for file_path in processing_files:
                try:
                    # Перемещаем файл обратно в папку upload
                    from config.settings import settings
                    import shutil
                    
                    destination = settings.UPLOAD_DIR / file_path.name
                    
                    # Проверяем что файл существует
                    if not file_path.exists():
                        logger.warning("migrate_processing.file.not_found", 
                                    file=file_path.name)
                        failed_count += 1
                        continue
                    
                    shutil.move(str(file_path), str(destination))
                    
                    migrated_count += 1
                    migrated_files.append(destination)  # Добавляем в список возврата
                    
                    logger.info("migrate_processing.file.moved",
                            file=file_path.name,
                            destination=str(destination))
                    
                except Exception as e:
                    failed_count += 1
                    logger.error("migrate_processing.file.failed",
                            file=file_path.name,
                            error=str(e))
            
            logger.info("migrate_processing.completed",
                    migrated_count=migrated_count,
                    failed_count=failed_count,
                    total=len(processing_files))
            
        except Exception as e:
            logger.error("migrate_processing.error", error=str(e))
        
        return migrated_files  # ✅ НОВОЕ: Возвращаем список мигрированных файлов
