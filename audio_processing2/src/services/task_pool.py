import asyncio
import time
from typing import List, Optional, Dict, Any
from pathlib import Path
import structlog

from config.settings import settings
from src.core.exceptions import ServiceError

logger = structlog.get_logger()


class TaskPool:
    """
    Пул обработки файлов с поддержкой:
    - Параллельной обработки файлов
    - Ограничения concurrent операций
    - Graceful shutdown
    - Hot-reload конфигурации
    - Метрик и логирования
    """

    def __init__(
        self,
        transcription_service,
        api_client,
        file_manager,
        metrics,
        max_concurrent_tasks: int = 3,
        max_transcription_calls: int = 3,
        max_api_calls: int = 5,
        queue_max_size: int = 100,
    ):
        """Инициализация TaskPool"""
        self.transcription_service = transcription_service
        self.api_client = api_client
        self.file_manager = file_manager
        self.metrics = metrics

        # Параметры
        self.max_concurrent_tasks = max_concurrent_tasks
        self.max_transcription_calls = max_transcription_calls
        self.max_api_calls = max_api_calls

        # Семафоры для ограничения concurrent операций
        self.transcription_sem = asyncio.Semaphore(max_transcription_calls)
        self.api_sem = asyncio.Semaphore(max_api_calls)

        # Очередь задач
        self.task_queue = asyncio.Queue(maxsize=queue_max_size)
        self.tasks: List[asyncio.Task] = []

        # Флаги состояния
        self.is_running = False
        self.is_paused = False
        self.pause_event = asyncio.Event()
        self.pause_event.set()

        # Статистика
        self.processed_count = 0
        self.failed_count = 0
        self.queue_full_events = 0

        logger.debug(
            "task_pool.initialized",
            max_workers=max_concurrent_tasks,
            max_transcription_calls=max_transcription_calls,
            max_api_calls=max_api_calls,
        )

    def get_bucket_name(self, bucket_type: str) -> str:
        """Получить имя bucket'а (MinIO или Local)"""
        if settings.USE_MINIO:
            bucket_map = {
                "upload": settings.MINIO_UPLOADS_BUCKET,
                "processing": settings.MINIO_PROCESSING_BUCKET,
                "processed": settings.MINIO_PROCESSED_BUCKET,
                "json": settings.MINIO_JSON_OUTPUT_BUCKET,
            }
        else:
            bucket_map = {
                "upload": str(settings.UPLOAD_DIR),
                "processing": str(settings.PROCESSING_DIR),
                "processed": str(settings.PROCESSED_DIR),
                "json": str(settings.JSON_OUTPUT_DIR),
            }
        return bucket_map.get(bucket_type)

    async def start(self) -> None:
        """Запустить пул задач с N worker'ами"""
        if self.is_running:
            return

        logger.info(
            "task.pool.starting",
            tasks=self.max_concurrent_tasks,
        )

        self.is_running = True
        self.is_paused = False
        self.pause_event.set()

        # Создать N worker'ов
        for i in range(self.max_concurrent_tasks):
            task = asyncio.create_task(self.worker(i))
            self.tasks.append(task)
            logger.debug("worker.created", worker_id=i)

        logger.info("task.pool.started")

    async def stop(self, timeout: int = 15) -> None:
        """
        Остановить пул задач с гарантией завершения всех worker'ов.
        
        Args:
            timeout: Максимальное время ожидания завершения worker'ов (сек)
        """
        if not self.is_running:
            return

        logger.info("task.pool.stopping", workers_count=len(self.tasks))
        self.is_running = False
        self.is_paused = False
        self.pause_event.set()

        # Добавить сигналы завершения для всех worker'ов
        num_workers = len(self.tasks)
        for i in range(num_workers):
            try:
                self.task_queue.put_nowait(None)
                logger.debug("worker.stop.signal.sent", worker_id=i)
            except asyncio.QueueFull:
                logger.warning("task.queue.full.during.stop")
                break

        # Ждать завершения всех worker'ов
        try:
            logger.info("task.pool.waiting.for.workers", timeout=timeout)
            results = await asyncio.wait_for(
                asyncio.gather(*self.tasks, return_exceptions=True),
                timeout=timeout,
            )
            logger.info("task.pool.all.workers.completed")

            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.warning(
                        "worker.failed.with.exception",
                        worker_id=i,
                        error=str(result),
                    )

        except asyncio.TimeoutError:
            logger.warning(
                "task.pool.shutdown.timeout",
                timeout=timeout,
                workers_count=len(self.tasks),
            )

            # Отменить оставшихся worker'ов
            logger.info("task.pool.cancelling.remaining.workers")
            for i, task in enumerate(self.tasks):
                if not task.done():
                    logger.warning("worker.cancelling", worker_id=i)
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        logger.debug("worker.cancelled.successfully", worker_id=i)
                    except Exception as e:
                        logger.warning(
                            "worker.cancellation.error",
                            worker_id=i,
                            error=str(e),
                        )

        # Очистить список tasks
        self.tasks.clear()
        logger.info("task.pool.stopped", workers_stopped=num_workers)

    async def add_task(self, filename: str) -> None:
        """
        Добавить файл в очередь обработки.
        
        Args:
            filename: Имя файла для обработки
            
        Raises:
            ServiceError: Если TaskPool не запущен или очередь переполнена
        """
        if not self.is_running:
            raise ServiceError("TaskPool is not running")

        if isinstance(filename, Path):
            filename = filename.name

        try:
            self.task_queue.put_nowait(filename)
            logger.debug("task.added.to.queue", file=filename)
        except asyncio.QueueFull:
            self.queue_full_events += 1
            logger.warning(
                "task.queue.full",
                file=filename,
                queue_size=self.task_queue.qsize(),
            )
            raise ServiceError("Task queue is full")

    async def worker(self, worker_id: int) -> None:
        """
        Worker loop - обрабатывает файлы из очереди.
        
        Args:
            worker_id: ID worker'а для логирования
        """
        logger.info("worker.started", worker_id=worker_id)

        try:
            while self.is_running:
                # Проверить pause
                await self.pause_event.wait()

                try:
                    # Получить файл из очереди (timeout 1 сек)
                    filename = await asyncio.wait_for(
                        self.task_queue.get(),
                        timeout=1.0,
                    )

                    # None = сигнал завершения
                    if filename is None:
                        logger.debug(
                            "worker.received.stop.signal",
                            worker_id=worker_id,
                        )
                        break

                    logger.debug(
                        "worker.processing",
                        worker_id=worker_id,
                        file=filename,
                    )

                    # Обработать файл
                    await self.process_file(filename)

                except asyncio.TimeoutError:
                    # Нет файлов в очереди - продолжаем ждать
                    continue

                except Exception as e:
                    logger.error(
                        "task.unexpected.error",
                        task_id=worker_id,
                        error=str(e),
                    )
                    self.failed_count += 1

        except asyncio.CancelledError:
            logger.info("worker.cancelled", worker_id=worker_id)
        finally:
            logger.info("worker.stopped", worker_id=worker_id)

    async def process_file(self, filename: str) -> None:
        """
        Полный процесс обработки файла:
        1. Переместить из upload → processing
        2. Получить данные файла из MinIO
        3. Отправить на транскрипцию (БЕЗ ВРЕМЕННОГО ФАЙЛА!)
        4. Получить результаты
        5. Сохранить JSON
        6. Отправить на API
        7. Переместить в processed
        
        Args:
            filename: Имя файла для обработки
        """
        start_time = time.time()
        processing_file = None
        file_bytes = None

        try:
            logger.info("file.processing.start", file=filename)

            # Получить имена bucket'ов
            upload_bucket = self.get_bucket_name("upload")
            processing_bucket = self.get_bucket_name("processing")
            processed_bucket = self.get_bucket_name("processed")

            logger.debug(
                "buckets.info",
                upload=upload_bucket,
                processing=processing_bucket,
                processed=processed_bucket,
            )

            # ========== ШАГ 1: Переместить файл ==========
            logger.debug("file.move.starting", file=filename, from_="upload", to="processing")
            
            processing_file = await self.file_manager.move_file(
                source_bucket=upload_bucket,
                destination_bucket=processing_bucket,
                object_name=filename,
            )

            if not processing_file:
                logger.error("file.move.failed", file=filename)
                self.failed_count += 1
                return

            logger.debug("file.moved.to.processing", file=filename)

            # ========== ШАГ 2: Получить данные файла ==========
            logger.debug("file.data.retrieval.starting", file=filename)
            
            file_bytes = await self.file_manager.storage.get_file_data(
                bucket=processing_bucket,
                object_name=filename,
            )

            if not file_bytes:
                logger.error("file.data.retrieval.failed", file=filename)
                self.failed_count += 1
                return

            logger.debug(
                "file.data.retrieved",
                file=filename,
                size=len(file_bytes),
                size_mb=round(len(file_bytes) / 1024 / 1024, 2),
            )

            # ========== ШАГ 3: Отправить на транскрипцию ==========
            # ✅ БЕЗ ВРЕМЕННОГО ФАЙЛА! Отправляем байты напрямую
            
            async with self.transcription_sem:
                logger.debug(
                    "transcription.submission.starting",
                    file=filename,
                )
                
                job_id = await self.transcription_service.submit_transcription_job(
                    file_bytes=file_bytes,  # ✅ Байты напрямую!
                    filename=filename,       # ✅ Только имя файла!
                )

                if not job_id:
                    logger.error("transcription.submission.failed", file=filename)
                    self.failed_count += 1
                    return

                logger.debug(
                    "transcription.submitted",
                    file=filename,
                    job_id=job_id,
                )

            # ========== ШАГ 4: Получить результаты транскрипции ==========
            logger.debug(
                "transcription.polling.starting",
                file=filename,
                job_id=job_id,
            )
            
            transcription_result = await self.transcription_service.poll_transcription_result(
                job_id
            )

            if not transcription_result:
                logger.error(
                    "transcription.result.retrieval.failed",
                    file=filename,
                    job_id=job_id,
                )
                self.failed_count += 1
                return

            logger.debug(
                "transcription.result.retrieved",
                file=filename,
                job_id=job_id,
            )

            # ========== ШАГ 5: Сохранить JSON результат ==========
            logger.debug("json.result.save.starting", file=filename)
            
            json_result = transcription_result
            json_name = await self.file_manager.save_transcription_result(
                json_result,
                filename,
            )

            if not json_name:
                logger.error("json.result.save.failed", file=filename)
                self.failed_count += 1
                return

            logger.debug("json.result.saved", file=filename, json_name=json_name)

            # ========== ШАГ 6: Отправить на API backend ==========
            async with self.api_sem:
                logger.debug("api.send.starting", file=filename)
                
                api_success = await self.api_client.send_transcription_result(
                    json_result,
                    filename,
                )

                if not api_success:
                    logger.error("api.send.failed", file=filename)
                    self.failed_count += 1
                    return

                logger.debug("api.result.sent", file=filename)

            # ========== ШАГ 7: Переместить в processed ==========
            logger.debug("file.final.move.starting", file=filename)
            
            final_file = await self.file_manager.move_file(
                source_bucket=processing_bucket,
                destination_bucket=processed_bucket,
                object_name=filename,
            )

            if not final_file:
                logger.error("file.final.move.failed", file=filename)
                self.failed_count += 1
                return

            logger.debug("file.moved.to.processed", file=filename)

            # ========== УСПЕХ! ==========
            elapsed = time.time() - start_time
            self.processed_count += 1

            logger.info(
                "file.processing.complete",
                file=filename,
                elapsed=f"{elapsed:.2f}s",
                processed_total=self.processed_count,
            )

            # Записать метрики
            if self.metrics:
                try:
                    await self.metrics.record_successful_processing(
                        filename=filename,
                        processing_time=elapsed,
                        size_bytes=len(file_bytes) if file_bytes else 0,
                    )
                    logger.debug(
                        "metrics.success.recorded",
                        file=filename,
                        processing_time=f"{elapsed:.2f}s",
                    )
                except Exception as metric_error:
                    logger.warning(
                        "metrics.record.success.failed",
                        file=filename,
                        error=str(metric_error),
                    )

        except Exception as e:
            logger.error(
                "file.processing.error",
                file=filename,
                error=str(e),
            )
            self.failed_count += 1

            # Записать метрики ошибки
            if self.metrics:
                try:
                    elapsed = time.time() - start_time
                    await self.metrics.record_failed_processing(
                        filename=filename,
                        processing_time=elapsed,
                        error=str(e),
                    )
                    logger.debug(
                        "metrics.failed.recorded",
                        file=filename,
                        error=str(e),
                    )
                except Exception as metric_error:
                    logger.warning(
                        "metrics.record.failed.failed",
                        error=str(metric_error),
                    )

        finally:
            # Вернуть файл в upload если что-то пошло не так
            if processing_file:
                try:
                    upload_bucket = self.get_bucket_name("upload")
                    processing_bucket = self.get_bucket_name("processing")
                    
                    await self.file_manager.move_file(
                        source_bucket=processing_bucket,
                        destination_bucket=upload_bucket,
                        object_name=filename,
                    )
                    logger.info("file.returned.to.upload", file=filename)
                except Exception as move_error:
                    logger.error(
                        "file.return.failed",
                        file=filename,
                        error=str(move_error),
                    )

            # Очистить переменные
            file_bytes = None

    async def pause(self) -> None:
        """Приостановить обработку файлов"""
        if self.is_paused:
            return

        logger.info("task.pool.pausing")
        self.is_paused = True
        self.pause_event.clear()

    async def resume(self) -> None:
        """Возобновить обработку файлов"""
        if not self.is_paused:
            return

        logger.info("task.pool.resuming")
        self.is_paused = False
        self.pause_event.set()

    def get_status(self) -> Dict[str, Any]:
        """Получить статус TaskPool"""
        return {
            "is_running": self.is_running,
            "is_paused": self.is_paused,
            "queue_size": self.task_queue.qsize(),
            "processed": self.processed_count,
            "failed": self.failed_count,
            "queue_full_events": self.queue_full_events,
        }