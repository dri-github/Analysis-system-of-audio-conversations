# main.py
import logging
import sys
import os
import signal

# Добавляем корневую директорию в путь для импортов
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Импортируем функцию настройки логирования
from logging_config import configure_structured_logging

from monitor.folder_watcher import start_monitoring

def signal_handler(signum, frame):
    """Обработчик сигналов для graceful shutdown"""
    logging.info("🛑 Received shutdown signal")
    sys.exit(0)

if __name__ == "__main__":
    # НАСТРАИВАЕМ ЛОГИРОВАНИЕ ТОЛЬКО ЗДЕСЬ
    logger = configure_structured_logging()
    
    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Основная логика приложения
    logger.info(
        "System Starting",
        extra={
            'component': 'audio_processing_system',
            'watch_folder': os.getenv('WATCH_FOLDER', './audio_uploads'),
            'max_workers': os.getenv('MAX_WORKERS', '3'),
            'log_level': 'INFO',
            'python_version': sys.version,
            'working_directory': os.getcwd()
        }
    )
    
    try:
        start_monitoring()
    except KeyboardInterrupt:
        logger.info("Stopped by user")
    except Exception as e:
        logger.error(f"Failed to start monitoring: {e}")
        sys.exit(1)