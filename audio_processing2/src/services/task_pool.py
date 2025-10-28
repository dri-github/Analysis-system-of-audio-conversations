"""
Улучшенный TaskPool с таймаутом при остановке.
"""
import asyncio
import time
from typing import List, Optional, Dict, Any
from pathlib import Path
import structlog

from src.core.exceptions import ServiceError

logger = structlog.get_logger()


class TaskPool:
    """Управление пулом асинхронных задач для обработки файлов"""
    
    def __init__(
        self, 
        transcription_service,
        api_client,
        file_manager,
        metrics,
        max_concurrent_tasks: int = 3,
        max_transcription_calls: int = 3,
        max_api_calls: int = 5,
        queue_max_size: int = 100
    ):
        self.transcription_service = transcription_service
        self.api_client = api_client
        self.file_manager = file_manager
        self.metrics = metrics
        
        self.max_concurrent_tasks = max_concurrent_tasks
        
        # Отдельные семафоры для разных операций
        self.transcription_sem = asyncio.Semaphore(max_transcription_calls)
        self.api_sem = asyncio.Semaphore(max_api_calls)
        
        # Очередь с ограничением размера
        self.task_queue = asyncio.Queue(maxsize=queue_max_size)
        self.tasks: List[asyncio.Task] = []
        self.is_running = False
        self.is_paused = False
        self.pause_event = asyncio.Event()
        self.pause_event.set()
        
        # Статистика
        self.processed_count = 0
        self.failed_count = 0
        self.queue_full_events = 0

    async def start(self) -> None:
        """Запуск пула задач"""
        if self.is_running:
            return

        logger.info("task.pool.starting", tasks=self.max_concurrent_tasks)
        
        self.is_running = True
        self.is_paused = False
        self.pause_event.set()
        
        self.tasks = [
            asyncio.create_task(self._task_loop(i), name=f"audio-task-{i}")
            for i in range(self.max_concurrent_tasks)
        ]
        
        logger.info("task.pool.started", tasks_count=len(self.tasks))

    async def stop(self) -> None:
        """Остановка пула задач с таймаутом"""
        if not self.is_running:
            return

        logger.info("task.pool.stopping")
        self.is_running = False
        self.is_paused = False
        self.pause_event.set()
        
        # ✅ НОВОЕ: Ждем завершения с таймаутом (максимум 5 сек)
        try:
            await asyncio.wait_for(
                self.task_queue.join(),
                timeout=5.0
            )
            logger.info("task.pool.all.tasks.completed")
        except asyncio.TimeoutError:
            logger.warning("task.pool.stop.timeout", 
                          pending_tasks=self.task_queue.qsize())
        
        # Отменяем задачи
        for task in self.tasks:
            task.cancel()
            
        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.tasks.clear()
        
        logger.info("task.pool.stopped",
                   processed=self.processed_count,
                   failed=self.failed_count)

    async def pause(self) -> None:
        """
        Приостановка обработки задач с корректной обработкой текущих операций.
        
        Гарантирует что:
        1. Текущие задачи завершат обработку (или будут отменены с таймаутом)
        2. Новые задачи не будут приняты
        3. При RESUME приложение корректно возобновится
        """
        if not self.is_running or self.is_paused:
            return

        logger.info("task.pool.pausing")
        self.is_paused = True
        self.pause_event.clear()
        
        logger.info("task.pool.paused", 
                active_tasks=self.get_active_tasks(),
                queue_size=self.get_queue_size())

    async def resume(self) -> None:
        """
        Возобновление обработки задач.
        
        Гарантирует что:
        1. Pause event устанавливается (все потоки пробуждаются)
        2. Обработка корректно возобновляется
        3. Нет потери данных
        """
        if not self.is_running or not self.is_paused:
            return

        logger.info("task.pool.resuming")
        self.is_paused = False
        self.pause_event.set()  # ← Это пробуждает ВСЕ ожидающие задачи
        
        logger.info("task.pool.resumed",
                active_tasks=self.get_active_tasks(),
                queue_size=self.get_queue_size())

    async def add_task(self, file_path: Path) -> None:
        """Добавление задачи в очередь"""
        if not self.is_running:
            raise ServiceError("Task pool is not running")
        
        try:
            await asyncio.wait_for(
                self.task_queue.put(file_path),
                timeout=5.0
            )
            logger.debug("task.added", file=file_path.name)
            
        except asyncio.TimeoutError:
            self.queue_full_events += 1
            logger.error("queue.full", 
                        file=file_path.name,
                        queue_size=self.task_queue.qsize(),
                        events=self.queue_full_events)
            raise ServiceError("Task queue is full")

    async def _task_loop(self, task_id: int) -> None:
        """Цикл работы задачи с поддержкой метрик"""
        task_logger = logger.bind(task_id=task_id)
        task_logger.info("task.started")
        
        while self.is_running:
            try:
                await self.pause_event.wait()
                
                try:
                    file_path = await asyncio.wait_for(
                        self.task_queue.get(), 
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                await self.pause_event.wait()
                
                task_logger.info("task.processing.file", file=file_path.name)
                
                start_time = time.time()
                success = await self._process_file(file_path, task_id)
                processing_time = time.time() - start_time
                
                if success:
                    self.processed_count += 1
                    
                    # Передаем filename, время и размер файла
                    file_size = file_path.stat().st_size if file_path.exists() else 0
                    await self.metrics.record_successful_processing(
                        filename=file_path.name,              # ← имя файла
                        processing_time=processing_time,      # ← время обработки
                        size_bytes=file_size                  # ← размер файла
                    )
                    
                    # Добавляем к текущей сессии
                    self.metrics.add_session_successful(processing_time)
                    
                    task_logger.info("task.file.processed.success", 
                                file=file_path.name,
                                time=processing_time)
                else:
                    self.failed_count += 1
                    
                    # Передаем filename и причину ошибки
                    error_message = "Processing failed"  # или конкретная ошибка если она есть
                    await self.metrics.record_failed_processing(
                        filename=file_path.name,              # ← имя файла
                        processing_time=processing_time,      # ← время обработки
                        error=error_message                   # ← описание ошибки
                    )
                    
                    # Добавляем ошибку к текущей сессии
                    self.metrics.add_session_failed()
                    
                    task_logger.error("task.file.processed.failed", file=file_path.name)

                
                await self.pause_event.wait()
                self.task_queue.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                task_logger.error("task.unexpected.error", error=str(e))
                self.failed_count += 1
                
                # ✅ НОВОЕ: Записываем неожиданную ошибку
                await self.metrics.record_failed_processing()
                self.metrics.add_session_failed()
                
                self.task_queue.task_done()

        task_logger.info("task.stopped")

    async def _process_file(self, file_path: Path, task_id: int) -> bool:
        """Обработка одного файла"""
        try:
            if not self.file_manager.validate_audio_file(file_path):
                logger.warning("file.validation.failed", file=file_path.name)
                return False
            
            processing_file = self.file_manager.move_to_processing(file_path)
            if not processing_file:
                return False
            
            async with self.transcription_sem:
                transcription_result = await self.transcription_service.transcribe_audio(
                    str(processing_file)
                )
            
            if not transcription_result:
                return False
            
            json_path = self.file_manager.save_transcription_result(
                transcription_result, 
                processing_file
            )
            if not json_path:
                return False
            
            async with self.api_sem:
                api_success = await self.api_client.send_transcription_result(
                    transcription_result, 
                    str(processing_file)
                )
            
            if not api_success:
                logger.warning("api.send.failed", file=file_path.name)
            
            processed_path = self.file_manager.move_to_processed(processing_file)
            if not processed_path:
                logger.warning("move.processed.failed", file=file_path.name)
            
            return True
            
        except Exception as e:
            logger.error("file.processing.error", 
                        file=file_path.name, 
                        task_id=task_id,
                        error=str(e))
            return False

    async def get_status(self) -> Dict[str, Any]:
        """Получение статуса пула задач"""
        return {
            "is_running": self.is_running,
            "is_paused": self.is_paused,
            "tasks_total": len(self.tasks),
            "tasks_active": sum(1 for t in self.tasks if not t.done()),
            "queue_size": self.task_queue.qsize(),
            "queue_max_size": self.task_queue.maxsize,
            "processed_total": self.processed_count,
            "failed_total": self.failed_count,
            "queue_full_events": self.queue_full_events,
            "success_rate": (
                self.processed_count / (self.processed_count + self.failed_count) * 100
                if (self.processed_count + self.failed_count) > 0 else 0
            )
        }

    def get_queue_size(self) -> int:
        """Получение размера очереди"""
        return self.task_queue.qsize()
    
    def get_active_tasks(self) -> int:
        """Получение количества активных задач"""
        return sum(1 for t in self.tasks if not t.done())
