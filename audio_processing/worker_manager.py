# worker_manager.py
import asyncio
import queue
import threading
from typing import Dict, List
from workers.transcription_worker import process_audio_files
from config import Config
from logging_config import get_component_logger

logger = get_component_logger("worker_manager")

class AsyncWorkerManager:
    def __init__(self):
        self.task_queue = queue.Queue()
        self.workers: Dict[int, threading.Thread] = {}
        self.worker_status: Dict[int, bool] = {}
        self.next_worker_id = 0
        self.is_running = True
        self.batch_size = Config.MAX_CONCURRENT_TRANSCRIPTIONS

    def add_task(self, file_path: str):
        self.task_queue.put(file_path)
        logger.info("task_added_to_queue", file_path=file_path, queue_size=self.task_queue.qsize())

    def start_workers(self):
        for i in range(Config.MAX_WORKERS):
            self._start_single_worker()
        logger.info("workers_started", worker_count=Config.MAX_WORKERS)

    def _start_single_worker(self):
        worker_id = self.next_worker_id
        self.next_worker_id += 1
        
        worker_thread = threading.Thread(
            target=self._worker_loop,
            args=(worker_id,),
            name=f"AsyncAudioWorker-{worker_id}",
            daemon=True
        )
        
        self.workers[worker_id] = worker_thread
        self.worker_status[worker_id] = True
        worker_thread.start()
        
        logger.info("worker_started", worker_id=worker_id)

    def _worker_loop(self, worker_id: int):
        """Цикл работы асинхронного воркера"""
        worker_logger = get_component_logger(f"worker_{worker_id}")
        
        # Создаем отдельный event loop для каждого воркера
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Создаем семафор БЕЗ параметра loop
        semaphore = asyncio.Semaphore(Config.MAX_CONCURRENT_TRANSCRIPTIONS)
        
        try:
            while self.is_running:
                try:
                    # Собираем батч файлов для обработки
                    file_batch = []
                    while len(file_batch) < self.batch_size:
                        try:
                            file_path = self.task_queue.get(timeout=1)
                            file_batch.append(file_path)
                        except queue.Empty:
                            break
                    
                    if file_batch:
                        self.worker_status[worker_id] = False
                        worker_logger.info("worker_processing_batch", file_count=len(file_batch), worker_id=worker_id)
                        
                        try:
                            # Асинхронная обработка батча с передачей семафора
                            results = loop.run_until_complete(process_audio_files(file_batch, semaphore))
                            
                            success_count = sum(1 for r in results if r)
                            worker_logger.info("worker_batch_completed", 
                                             success_count=success_count,
                                             total_count=len(file_batch),
                                             worker_id=worker_id)
                            
                        except Exception as e:
                            worker_logger.error("worker_batch_error", error=str(e), worker_id=worker_id)
                        
                        finally:
                            self.worker_status[worker_id] = True
                            # Помечаем задачи как выполненные
                            for _ in file_batch:
                                self.task_queue.task_done()
                    
                except Exception as e:
                    worker_logger.error("worker_unexpected_error", error=str(e), worker_id=worker_id)
        
        finally:
            loop.close()

    def get_queue_size(self):
        return self.task_queue.qsize()
    
    def get_worker_status(self):
        busy_workers = sum(1 for status in self.worker_status.values() if not status)
        free_workers = sum(1 for status in self.worker_status.values() if status)
        
        return {
            'queue_size': self.get_queue_size(),
            'workers_total': len(self.workers),
            'workers_busy': busy_workers,
            'workers_free': free_workers
        }
    
    def stop_workers(self):
        self.is_running = False
        logger.warning("workers_stopping", active_workers=len(self.workers), pending_tasks=self.task_queue.qsize())
        
        for worker_id, thread in self.workers.items():
            thread.join(timeout=5)
            if thread.is_alive():
                logger.warning("worker_stop_timeout", worker_id=worker_id)
            else:
                logger.info("worker_stopped", worker_id=worker_id)
            
        logger.info("all_workers_stopped", total_stopped=len(self.workers))

# Глобальный экземпляр
worker_manager = AsyncWorkerManager()