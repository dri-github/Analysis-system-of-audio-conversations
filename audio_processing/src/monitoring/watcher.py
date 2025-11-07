import asyncio
from pathlib import Path
from typing import Set, Dict, Any, Optional

from config.settings import settings
from src.core.exceptions import ServiceError
import structlog

logger = structlog.get_logger()


class Watcher:
    """Мониторинг bucket/папки на появление новых аудиофайлов"""

    def __init__(self, file_manager, task_pool, scan_interval: int = 2):
        """
        Инициализация наблюдателя.

        Args:
            file_manager: Менеджер файлов
            task_pool: Пул задач для обработки
            scan_interval: Интервал сканирования в секундах
        """
        self.file_manager = file_manager
        self.task_pool = task_pool
        self.scan_interval = scan_interval
        self.is_running = False
        self.is_paused = False
        self.processed_files: Set[str] = set()  # Теперь хранит имена файлов, а не Path
        self.scan_task: Optional[asyncio.Task] = None
        self.pause_event = asyncio.Event()
        self.pause_event.set()  # Изначально не на паузе

    async def start(self) -> None:
        """Запуск мониторинга bucket/папки"""
        if self.is_running:
            return

        bucket_name = settings.MINIO_UPLOADS_BUCKET if settings.USE_MINIO else str(settings.UPLOAD_DIR)
        logger.info(
            "watcher.starting",
            watch_location=bucket_name,
            scan_interval=self.scan_interval,
            storage_type="minio" if settings.USE_MINIO else "local"
        )

        self.is_running = True
        self.is_paused = False
        self.pause_event.set()
        self.scan_task = asyncio.create_task(self._scan_loop())

        logger.info("watcher.started")

    async def stop(self) -> None:
        """Остановка мониторинга"""
        if not self.is_running:
            return

        logger.info("watcher.stopping")
        self.is_running = False
        self.is_paused = False
        self.pause_event.set()

        if self.scan_task:
            self.scan_task.cancel()
            try:
                await self.scan_task
            except asyncio.CancelledError:
                pass

        logger.info("watcher.stopped")

    async def pause(self) -> None:
        """Приостановка сканирования"""
        if not self.is_running or self.is_paused:
            return

        logger.info("watcher.pausing")
        self.is_paused = True
        self.pause_event.clear()

        logger.info("watcher.paused")

    async def resume(self) -> None:
        """Возобновление сканирования"""
        if not self.is_running or not self.is_paused:
            return

        logger.info("watcher.resuming")
        self.is_paused = False
        self.pause_event.set()

        logger.info("watcher.resumed")

    async def _scan_loop(self) -> None:
        """Главный цикл сканирования bucket/папки"""
        while self.is_running:
            try:
                # Проверяем паузу
                await self.pause_event.wait()

                # Сканируем bucket/папку
                await self._scan_upload_location()

                # Ждем перед следующим сканированием
                await asyncio.sleep(self.scan_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("watcher.scan.error", error=str(e))
                await asyncio.sleep(self.scan_interval)

    async def _scan_upload_location(self) -> None:
        """Сканирование bucket/директории входящих файлов"""
        try:
            audio_files = await self.file_manager.get_audio_files(bucket_type="upload")
            
            for file_name in audio_files:
                # Пропускаем уже обработанные файлы
                if file_name in self.processed_files:
                    continue
                
                # ✅ ДОБАВИТЬ ПРОВЕРКУ ЗДЕСЬ:
                if not self.task_pool or not self.task_pool.is_running:
                    logger.debug("task_pool.not.ready.skipping.file",
                            file=file_name,
                            task_pool_exists=self.task_pool is not None,
                            task_pool_running=self.task_pool.is_running if self.task_pool else False)
                    await asyncio.sleep(1)
                    continue
                # ✅ ДО СЮДА
                
                # Валидируем файл
                is_valid = await self.file_manager.validate_audio_file(
                    bucket_type="upload",
                    object_name=file_name
                )
                
                if not is_valid:
                    logger.warning("file.validation.failed", file=file_name)
                    self.processed_files.add(file_name)
                    continue
                
                # Добавляем в очередь обработки
                try:
                    await self.task_pool.add_task(file_name)
                    self.processed_files.add(file_name)
                    logger.info("file.added.to.queue", file=file_name)
                except ServiceError as e:
                    logger.error("queue.error", file=file_name, error=str(e))
                    await asyncio.sleep(self.scan_interval * 2)
                except Exception as e:
                    logger.error("add.task.error", file=file_name, error=str(e))
        
        except Exception as e:
            bucket_name = settings.MINIO_UPLOADS_BUCKET if settings.USE_MINIO else str(settings.UPLOAD_DIR)
            logger.error(
                "scan.location.error",
                location=bucket_name,
                error=str(e)
            )


    async def get_status(self) -> Dict[str, Any]:
        """Получение статуса наблюдателя"""
        bucket_name = settings.MINIO_UPLOADS_BUCKET if settings.USE_MINIO else str(settings.UPLOAD_DIR)
        return {
            "is_running": self.is_running,
            "is_paused": self.is_paused,
            "watch_location": bucket_name,
            "processed_files_count": len(self.processed_files),
            "scan_interval": self.scan_interval,
            "storage_type": "minio" if settings.USE_MINIO else "local"
        }

    def get_processed_count(self) -> int:
        """Получить количество обработанных файлов"""
        return len(self.processed_files)

    def reset_processed_files(self) -> None:
        """Очистить список обработанных файлов"""
        logger.info("watcher.reset.processed.files")
        self.processed_files.clear()

    async def update_task_pool(self, new_task_pool) -> None:
        """
        Обновить экземпляр TaskPool (вызывается при перезагрузке конфигурации).

        Это безопасно обновляет ссылку на пул задач, убеждаясь что:
        1. Новый пул корректно установлен
        2. Сканирование продолжает работать с новым пулом
        3. Нет зависаний при переходе на новый пул
        """
        try:
            old_pool = self.task_pool
            old_pool_id = id(old_pool) if old_pool else None
            new_pool_id = id(new_task_pool)

            logger.info(
                "watcher.updating_task_pool",
                old_pool_id=old_pool_id,
                new_pool_id=new_pool_id
            )

            # Обновляем ссылку на пул
            self.task_pool = new_task_pool

            logger.info(
                "watcher.task_pool_updated",
                old_pool_id=old_pool_id,
                new_pool_id=new_pool_id
            )
        except Exception as e:
            logger.error("watcher.update_task_pool.failed", error=str(e))

    async def recover_processing_files(self) -> None:
        """
        Восстановление файлов из папки processing при перезапуске.

        Это помогает при сбоях: если файл был в процессе обработки
        и приложение упало, при перезапуске мы вернём его в очередь.
        """
        try:
            processing_files = await self.file_manager.get_processing_files()

            logger.info(
                "watcher.recovering.processing.files",
                count=len(processing_files)
            )

            # Перемещаем файлы обратно в upload bucket
            for file_name in processing_files:
                try:
                    success = await self.file_manager.move_file(
                        source_bucket="processing",
                        destination_bucket="upload",
                        object_name=file_name
                    )

                    if success:
                        # Очищаем файл из обработанных
                        self.processed_files.discard(file_name)
                        logger.info(
                            "file.recovered.from.processing",
                            file=file_name
                        )
                except Exception as e:
                    logger.error(
                        "file.recovery.failed",
                        file=file_name,
                        error=str(e)
                    )
        except Exception as e:
            logger.error("recover.processing.files.failed", error=str(e))