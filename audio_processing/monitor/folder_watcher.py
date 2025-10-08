# monitor/folder_watcher.py
import time
import os
from pathlib import Path
import structlog
from worker_manager import worker_manager
from config import Config

# Инициализация логгера
logger = structlog.get_logger()

class FolderWatcher:
    def __init__(self):
        self.processed_files = set()
        self._ensure_directories()
        
    def _ensure_directories(self):
        """Создает необходимые папки если они не существуют"""
        os.makedirs(Config.WATCH_FOLDER, exist_ok=True)
        os.makedirs(Config.PROCESSING_FOLDER, exist_ok=True)
        os.makedirs(Config.PROCESSED_FOLDER, exist_ok=True)
        logger.info(
            "directories.verified",
            watch_folder=Config.WATCH_FOLDER,
            processing_folder=Config.PROCESSING_FOLDER,
            processed_folder=Config.PROCESSED_FOLDER
        )

    def _is_audio_file(self, file_path):
        """Проверяет является ли файл аудиофайлом"""
        audio_extensions = {'.wav', '.mp3', '.m4a', '.flac', '.ogg'}
        return any(file_path.lower().endswith(ext) for ext in audio_extensions)

    def _move_to_processing(self, file_path):
        """Перемещает файл в папку processing"""
        filename = os.path.basename(file_path)
        processing_path = os.path.join(Config.PROCESSING_FOLDER, filename)
        
        try:
            os.rename(file_path, processing_path)
            logger.info(
                "file.moved.to.processing",
                original_path=file_path,
                processing_path=processing_path,
                filename=filename
            )
            return processing_path
        except OSError as e:
            logger.error(
                "file.move.failed",
                file_path=file_path,
                error=str(e),
                error_type=type(e).__name__
            )
            return None

    def scan_for_new_files(self):
        """Сканирует папку на наличие новых файлов"""
        try:
            current_files = set()
            new_files_count = 0
            
            for filename in os.listdir(Config.WATCH_FOLDER):
                file_path = os.path.join(Config.WATCH_FOLDER, filename)
                
                if (os.path.isfile(file_path) and 
                    self._is_audio_file(file_path) and 
                    file_path not in self.processed_files):
                    
                    logger.info(
                        "new.audio.file.detected",
                        filename=filename,
                        file_path=file_path
                    )
                    
                    # Перемещаем в processing
                    processing_path = self._move_to_processing(file_path)
                    if not processing_path:
                        continue
                    
                    # Добавляем задачу в очередь воркеров
                    worker_manager.add_task(processing_path)
                    self.processed_files.add(file_path)
                    new_files_count += 1
                
                elif os.path.isfile(file_path):
                    current_files.add(file_path)
            
            # Обновляем множество обработанных файлов
            self.processed_files = self.processed_files.intersection(current_files)
            
            if new_files_count > 0:
                logger.info(
                    "new.files.processed",
                    files_count=new_files_count,
                    total_processed_files=len(self.processed_files)
                )
            
        except Exception as e:
            logger.error(
                "folder.scan.error",
                error=str(e),
                error_type=type(e).__name__,
                watch_folder=Config.WATCH_FOLDER
            )

    def log_status(self):
        """Логирует статус системы"""
        status = worker_manager.get_worker_status()
        logger.info(
            "system.status",
            queue_size=status['queue_size'],
            workers_busy=status['workers_busy'],
            workers_total=status['workers_total'],
            workers_free=status['workers_free'],
            processed_files_count=len(self.processed_files),
            utilization_rate=f"{(status['workers_busy'] / status['workers_total']) * 100:.1f}%" if status['workers_total'] > 0 else "0%"
        )

def start_monitoring():
    """Запускает мониторинг папки"""
    watcher = FolderWatcher()
    worker_manager.autorize()
    # Запускаем воркеры
    worker_manager.start_workers()
    
    logger.info(
        "monitoring.started",
        watch_folder=Config.WATCH_FOLDER,
        max_workers=Config.MAX_WORKERS,
        queue_check_interval=Config.QUEUE_CHECK_INTERVAL,
        component="folder_watcher"
    )
    
    status_counter = 0
    scan_iteration = 0
    
    try:
        while True:
            scan_iteration += 1
            watcher.scan_for_new_files()
            
            # Логируем статус каждые 10 итераций
            status_counter += 1
            if status_counter >= 10:
                watcher.log_status()
                status_counter = 0
                
                # Дополнительное логирование каждые 50 итераций
                if scan_iteration % 50 == 0:
                    logger.info(
                        "monitoring.health.check",
                        total_iterations=scan_iteration,
                        total_processed_files=len(watcher.processed_files),
                        component="folder_watcher"
                    )
                
            time.sleep(Config.QUEUE_CHECK_INTERVAL)
            
    except KeyboardInterrupt:
        logger.info(
            "monitoring.stopped.by.user",
            total_iterations=scan_iteration,
            total_processed_files=len(watcher.processed_files)
        )
    except Exception as e:
        logger.error(
            "monitoring.fatal.error",
            error=str(e),
            error_type=type(e).__name__,
            total_iterations=scan_iteration,
            component="folder_watcher"
        )
    finally:
        worker_manager.stop_workers()
        logger.info(
            "monitoring.cleanup.completed",
            component="folder_watcher"
        )