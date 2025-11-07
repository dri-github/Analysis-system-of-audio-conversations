class AudioProcessingError(Exception):
    """Базовое исключение для приложения"""
    pass

class ApplicationError(AudioProcessingError):
    """Ошибка инициализации приложения"""
    pass

class ConfigurationError(AudioProcessingError):
    """Ошибка конфигурации"""
    pass

class ServiceError(AudioProcessingError):
    """Ошибка сервиса"""
    pass

class TranscriptionError(ServiceError):
    """Ошибка транскрипции"""
    pass

class APIError(ServiceError):
    """Ошибка API"""
    pass

class FileManagementError(AudioProcessingError):
    """Ошибка управления файлами"""
    pass