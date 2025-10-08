# logging_config.py
import logging
import sys
import os
from datetime import datetime

class ColorFormatter(logging.Formatter):
    """Форматтер с цветами для консоли"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green  
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        # Эмодзи для разных логгеров
        emoji_map = {
            'transcription_worker': '🎤',
            'folder_watcher': '👁️',
            'worker_manager': '👷',
            'root': '⚙️',
            'logging_config': '⚙️',
        }
        
        emoji = emoji_map.get(record.name.split('.')[-1], '📄')
        color = self.COLORS.get(record.levelname, '\033[37m')
        
        # Форматируем сообщение
        timestamp = datetime.now().strftime('%H:%M:%S')
        levelname = f"{color}{record.levelname:<8}{self.RESET}"
        message = f"{emoji} {record.getMessage()}"
        
        return f"\033[90m{timestamp}\033[0m {levelname} {message}"

def configure_structured_logging():
    """Настройка логирования - вызывается ОДИН раз в main.py"""
    
    # Создаем папку для логов
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_filename = os.path.join(log_dir, "audio_processing.log")
    
    # Очищаем существующие handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Handler для консоли с цветами
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(ColorFormatter())
    
    # Handler для файла (простой текст)
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    
    # Настраиваем логгер
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.setLevel(logging.INFO)
    
    # Отключаем логи для шумных библиотек
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    
    # Стартовое сообщение (вызывается только один раз)
    print("🎧" + "="*70)
    print("🎧 🚀 АУДИО ПРОЦЕССИНГ СИСТЕМА ЗАПУЩЕНА")
    print(f"🎧 📁 Папка мониторинга: ./audio_uploads")
    print(f"🎧 👥 Рабочие процессы: 3") 
    print(f"🎧 📝 Логи записываются в: {log_filename}")
    print("🎧" + "="*70)
    
    logger = logging.getLogger("main")
    logger.info("System Ready")
    
    return logger

