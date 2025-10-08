# logging_config.py
import logging
import sys
import os
from datetime import datetime
from pathlib import Path
import structlog

def setup_logging():
    """Настраивает структурированное логирование для всех компонентов"""
    
    # Создаем папку для логов если не существует
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Препроцессоры для structlog
    timestamper = structlog.processors.TimeStamper(fmt="iso")
    
    # Общие процессоры для консоли
    console_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        timestamper,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.dev.ConsoleRenderer(colors=True)  # Красивый вывод в консоль
    ]
    
    # Общие процессоры для файлов (JSON)
    file_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        timestamper,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()  # JSON для файлов
    ]
    
    # Настройка structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            timestamper,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Создаем корневой логгер
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Очищаем существующие handlers
    root_logger.handlers = []
    
    # Форматтер для консоли
    console_formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.dev.ConsoleRenderer(colors=True),
    )
    
    # Форматтер для файлов (JSON)
    file_formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(),
    )
    
    # Handler для консоли
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    
    # Handler для общего файлового лога
    general_log_file = log_dir / "general.log"
    file_handler = logging.FileHandler(general_log_file, encoding='utf-8', mode='a')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(file_formatter)
    
    # Добавляем handlers к корневому логгеру
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Отключаем логирование для некоторых noisy библиотек
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    
    return structlog.get_logger()

def get_component_logger(component_name: str):
    """Возвращает логгер для конкретного компонента с записью в отдельный файл"""
    logger = structlog.get_logger(component_name)
    
    # Создаем отдельный handler для компонента
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    component_log_file = log_dir / f"{component_name}.log"
    component_handler = logging.FileHandler(component_log_file, encoding='utf-8', mode='a')
    component_handler.setLevel(logging.INFO)
    
    # Форматтер для файла компонента (JSON)
    component_formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(),
    )
    component_handler.setFormatter(component_formatter)
    
    # Получаем логгер для компонента и добавляем handler
    component_python_logger = logging.getLogger(component_name)
    component_python_logger.setLevel(logging.INFO)
    component_python_logger.addHandler(component_handler)
    component_python_logger.propagate = True  # Пропускать в корневой логгер для консоли
    
    return logger.bind(component=component_name)

# Инициализация основного логгера
logger = setup_logging()