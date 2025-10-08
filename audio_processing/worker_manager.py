# worker_manager.py
import threading
import queue
import time
from typing import Dict, Optional
import structlog
from workers.transcription_worker import TranscriptionWorker
from config import Config

# Инициализация логгера
logger = structlog.get_logger()

class WorkerManager:
    def __init__(self):
        self.task_queue = queue.Queue()
        self.workers: Dict[int, threading.Thread] = {}
        self.worker_status: Dict[int, bool] = {}  # True - свободен, False - занят
        self.next_worker_id = 0
        self.is_running = True
        self.transcription_worker = TranscriptionWorker()
        
    def add_task(self, file_path: str):
        """Добавляет задачу в очередь"""
        self.task_queue.put(file_path)
        logger.info(
            "task.added.to.queue",
            file_path=file_path,
            queue_size=self.task_queue.qsize(),
            worker_id="manager"
        )
        
    def start_workers(self):
        """Запускает воркеры"""
        for i in range(Config.MAX_WORKERS):
            self._start_single_worker()
            
        logger.info(
            "workers.started",
            worker_count=Config.MAX_WORKERS,
            max_workers=Config.MAX_WORKERS
        )
        
    def _start_single_worker(self):
        """Запускает один воркер"""
        worker_id = self.next_worker_id
        self.next_worker_id += 1
        
        worker_thread = threading.Thread(
            target=self._worker_loop,
            args=(worker_id,),
            name=f"AudioWorker-{worker_id}",
            daemon=True
        )
        
        self.workers[worker_id] = worker_thread
        self.worker_status[worker_id] = True
        worker_thread.start()
        
        logger.info(
            "worker.started",
            worker_id=worker_id,
            thread_name=worker_thread.name
        )
        
    def _worker_loop(self, worker_id: int):
        """Цикл работы воркера"""
        worker_logger = logger.bind(worker_id=worker_id)
        
        while self.is_running:
            try:
                # Берем задачу из очереди с таймаутом
                file_path = self.task_queue.get(timeout=1)
                self.worker_status[worker_id] = False
                
                worker_logger.info(
                    "worker.processing.started",
                    file_path=file_path,
                    queue_size_remaining=self.task_queue.qsize()
                )
                
                try:
                    # Обрабатываем файл
                    success = self.transcription_worker.process_audio_file(file_path)
                    
                    if success:
                        worker_logger.info(
                            "worker.processing.completed",
                            file_path=file_path,
                            status="success"
                        )
                    else:
                        worker_logger.error(
                            "worker.processing.failed",
                            file_path=file_path,
                            status="failed"
                        )
                        
                except Exception as e:
                    worker_logger.error(
                        "worker.processing.error",
                        file_path=file_path,
                        error=str(e),
                        error_type=type(e).__name__
                    )
                    
                finally:
                    self.worker_status[worker_id] = True
                    self.task_queue.task_done()
                    
            except queue.Empty:
                # Очередь пуста, продолжаем ожидание
                continue
            except Exception as e:
                worker_logger.error(
                    "worker.unexpected.error",
                    error=str(e),
                    error_type=type(e).__name__
                )
                time.sleep(1)
                
    def get_queue_size(self):
        """Возвращает размер очереди"""
        return self.task_queue.qsize()
    
    def get_worker_status(self):
        """Возвращает статус воркеров"""
        busy_workers = sum(1 for status in self.worker_status.values() if not status)
        free_workers = sum(1 for status in self.worker_status.values() if status)
        
        return {
            'queue_size': self.get_queue_size(),
            'workers_total': len(self.workers),
            'workers_busy': busy_workers,
            'workers_free': free_workers
        }
    
    def log_system_status(self):
        """Логирует текущий статус системы"""
        status = self.get_worker_status()
        logger.info(
            "system.status.update",
            queue_size=status['queue_size'],
            workers_busy=status['workers_busy'],
            workers_free=status['workers_free'],
            workers_total=status['workers_total'],
            utilization_rate=f"{(status['workers_busy'] / status['workers_total']) * 100:.1f}%" if status['workers_total'] > 0 else "0%"
        )
    
    def stop_workers(self):
        """Останавливает воркеры"""
        self.is_running = False
        logger.warning(
            "workers.stopping",
            active_workers=len(self.workers),
            pending_tasks=self.task_queue.qsize()
        )
        
        for worker_id, thread in self.workers.items():
            thread.join(timeout=5)
            if thread.is_alive():
                logger.warning(
                    "worker.stop.timeout",
                    worker_id=worker_id
                )
            else:
                logger.info(
                    "worker.stopped",
                    worker_id=worker_id
                )
            
        logger.info(
            "all.workers.stopped",
            total_stopped=len(self.workers)
        )
        
    def autorize(self):
        self.transcription_worker._get_x_access_token()
    
# Глобальный экземпляр менеджера воркеров
worker_manager = WorkerManager()