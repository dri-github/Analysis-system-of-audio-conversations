# main.py
import sys
import os
import signal

# Добавляем корневую директорию в путь для импортов
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from logging_config import get_component_logger
from monitor.folder_watcher import start_monitoring

# Получаем логгер для main
logger = get_component_logger("main")

def signal_handler(signum, frame):
    """Обработчик сигналов для graceful shutdown"""
    logger.info("shutdown.signal.received", signal_number=signum)
    sys.exit(0)

if __name__ == "__main__":
    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info(
        "system.starting",
        watch_folder=os.getenv("WATCH_FOLDER", "./audio_uploads"),
        max_workers=os.getenv("MAX_WORKERS", "3"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        python_version=sys.version,
        working_directory=os.getcwd()
    )

    try:
        start_monitoring()
    except KeyboardInterrupt:
        logger.info("system.stopped.by.user")
    except Exception as e:
        logger.error(
            "system.start.failed",
            error=str(e),
            error_type=type(e).__name__
        )
        sys.exit(1)