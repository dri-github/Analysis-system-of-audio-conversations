from datetime import datetime, timedelta
from typing import Dict, Any, List
import structlog

logger = structlog.get_logger()


class FileMetrics:
    """Метрики для одного файла"""
    def __init__(self, filename: str, processing_time: float, 
                 status: str, size_bytes: int = 0, error: str = None):
        self.filename = filename
        self.timestamp = datetime.now().isoformat() + "Z"  # ✅ ISO 8601 формат
        self.processing_time = processing_time
        self.status = status  # "success" или "failed"
        self.size_bytes = size_bytes
        self.error = error
        
        # Форматированное время для читабельности
        self.timestamp_readable = datetime.fromisoformat(
            self.timestamp.replace('Z', '+00:00')
        ).strftime("%Y-%m-%d %H:%M:%S")
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразовать в словарь"""
        data = {
            "filename": self.filename,
            "timestamp": self.timestamp,
            "timestamp_readable": self.timestamp_readable,
            "processing_time": round(self.processing_time, 2),
            "status": self.status,
            "size_bytes": self.size_bytes
        }
        if self.error:
            data["error"] = self.error
        return data


class MetricsCollector:
    """
    Сборщик метрик с полной информацией о времени обработки файлов.
    """
    
    # Глобальные счетчики
    all_time_successful = 0
    all_time_failed = 0
    all_time_seconds = 0.0
    start_time = datetime.now()
    
    # История по дням с полной информацией о файлах
    daily_history: Dict[str, Dict[str, Any]] = {}
    
    def __init__(self):
        """Инициализация сборщика метрик"""
        # Текущая сессия
        self.session_successful = 0
        self.session_failed = 0
        self.session_total_time = 0.0
        self.session_start_time = datetime.now()
        
        self.processing_times: List[float] = []
        
        self._initialize_today()
        
        logger.info("metrics.collector.initialized",
                   all_time_successful=self.all_time_successful,
                   all_time_failed=self.all_time_failed)
    
    @classmethod
    def _initialize_today(cls) -> None:
        """Инициализировать запись за сегодня"""
        today = datetime.now().strftime("%Y-%m-%d")
        if today not in cls.daily_history:
            cls.daily_history[today] = {
                "date": today,
                "successful": 0,
                "failed": 0,
                "total_time": 0.0,
                "files": []  # ✅ СПИСОК ФАЙЛОВ С МЕТАДАННЫМИ
            }
    
    @classmethod
    async def record_successful_processing(cls, filename: str, processing_time: float, 
                                          size_bytes: int = 0) -> None:
        """Записать успешную обработку файла с временной меткой"""
        # Глобальная история
        cls.all_time_successful += 1
        cls.all_time_seconds += processing_time
        
        # История по дням
        today = datetime.now().strftime("%Y-%m-%d")
        cls._initialize_today()
        
        # ✅ Сохраняем полную информацию о файле
        file_metrics = FileMetrics(
            filename=filename,
            processing_time=processing_time,
            status="success",
            size_bytes=size_bytes
        )
        
        cls.daily_history[today]["successful"] += 1
        cls.daily_history[today]["total_time"] += processing_time
        cls.daily_history[today]["files"].append(file_metrics.to_dict())
        
        logger.debug("metrics.successful_recorded",
                    filename=filename,
                    time=processing_time,
                    total_successful=cls.all_time_successful)
    
    @classmethod
    async def record_failed_processing(cls, filename: str, 
                                      processing_time: float = 0.0,
                                      error: str = None) -> None:
        """Записать ошибку при обработке файла с временной меткой"""
        # Глобальная история
        cls.all_time_failed += 1
        
        # История по дням
        today = datetime.now().strftime("%Y-%m-%d")
        cls._initialize_today()
        
        # ✅ Сохраняем полную информацию об ошибке
        file_metrics = FileMetrics(
            filename=filename,
            processing_time=processing_time,
            status="failed",
            error=error
        )
        
        cls.daily_history[today]["failed"] += 1
        cls.daily_history[today]["files"].append(file_metrics.to_dict())
        
        logger.debug("metrics.failed_recorded",
                    filename=filename,
                    error=error,
                    total_failed=cls.all_time_failed)
    
    # Методы текущей сессии
    def add_session_successful(self, processing_time: float) -> None:
        """Добавить успешную обработку к текущей сессии"""
        self.session_successful += 1
        self.session_total_time += processing_time
        self.processing_times.append(processing_time)
    
    def add_session_failed(self) -> None:
        """Добавить ошибку к текущей сессии"""
        self.session_failed += 1
    
    def reset_session_metrics(self) -> None:
        """Сбросить метрики текущей сессии"""
        logger.info("metrics.session.resetting",
                   successful=self.session_successful,
                   failed=self.session_failed)
        
        self.session_successful = 0
        self.session_failed = 0
        self.session_total_time = 0.0
        self.processing_times.clear()
        self.session_start_time = datetime.now()
    
    def _get_session_average_time(self) -> float:
        """Получить среднее время обработки за сессию"""
        if not self.processing_times:
            return 0.0
        return sum(self.processing_times) / len(self.processing_times)
    
    @classmethod
    def _get_all_time_average(cls) -> float:
        """Получить среднее время обработки за всю историю"""
        if cls.all_time_successful == 0:
            return 0.0
        return cls.all_time_seconds / cls.all_time_successful
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Получить все метрики"""
        total_session = self.session_successful + self.session_failed
        session_success_rate = (
            self.session_successful / total_session * 100 
            if total_session > 0 else 0
        )
        
        total_all_time = self.all_time_successful + self.all_time_failed
        all_time_success_rate = (
            self.all_time_successful / total_all_time * 100 
            if total_all_time > 0 else 0
        )
        
        session_elapsed = (datetime.now() - self.session_start_time).total_seconds()
        
        return {
            "current_session": {
                "successful": self.session_successful,
                "failed": self.session_failed,
                "total": total_session,
                "success_rate": round(session_success_rate, 2),
                "total_time_seconds": round(self.session_total_time, 2),
                "average_processing_time": round(self._get_session_average_time(), 2),
                "session_elapsed_seconds": round(session_elapsed, 2)
            },
            
            "all_time": {
                "successful": self.all_time_successful,
                "failed": self.all_time_failed,
                "total": total_all_time,
                "success_rate": round(all_time_success_rate, 2),
                "total_time_seconds": round(self.all_time_seconds, 2),
                "average_processing_time": round(self._get_all_time_average(), 2)
            },
            
            "daily": {
                "today": self._get_today_stats(),
                "last_7_days": self._get_last_n_days(7),
                "history": self.daily_history
            }
        }
    
    def _get_today_stats(self) -> Dict[str, Any]:
        """Получить статистику за сегодня"""
        today = datetime.now().strftime("%Y-%m-%d")
        if today not in self.daily_history:
            return self._create_empty_day_stats(today)
        
        stats = self.daily_history[today]
        total = stats["successful"] + stats["failed"]
        success_rate = (
            stats["successful"] / total * 100 if total > 0 else 0
        )
        
        return {
            "date": today,
            "successful": stats["successful"],
            "failed": stats["failed"],
            "total": total,
            "success_rate": round(success_rate, 2),
            "total_time": round(stats["total_time"], 2),
            "files": stats["files"]  # ✅ Список файлов с временными метками
        }
    
    def _get_last_n_days(self, days: int) -> List[Dict[str, Any]]:
        """Получить статистику за последние N дней"""
        result = []
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            if date in self.daily_history:
                stats = self.daily_history[date]
                total = stats["successful"] + stats["failed"]
                success_rate = (
                    stats["successful"] / total * 100 if total > 0 else 0
                )
                result.append({
                    "date": date,
                    "successful": stats["successful"],
                    "failed": stats["failed"],
                    "total": total,
                    "success_rate": round(success_rate, 2),
                    "total_time": round(stats["total_time"], 2),
                    "files_count": len(stats["files"])
                })
        return result
    
    # ✅ НОВЫЕ МЕТОДЫ ДЛЯ ПОИСКА ПО ВРЕМЕНИ
    
    async def get_files_by_date(self, date: str) -> List[Dict[str, Any]]:
        """Получить все файлы обработанные в конкретный день (2025-10-27)"""
        if date not in self.daily_history:
            return []
        
        return self.daily_history[date]["files"]
    
    async def get_files_from_last_n_days(self, days: int) -> List[Dict[str, Any]]:
        """Получить все файлы за последние N дней"""
        all_files = []
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            if date in self.daily_history:
                all_files.extend(self.daily_history[date]["files"])
        return all_files
    
    async def get_files_by_status(self, status: str, date: str = None) -> List[Dict[str, Any]]:
        """Получить файлы по статусу (success/failed) за конкретный день или всю историю"""
        result = []
        
        if date:
            # За конкретный день
            if date in self.daily_history:
                for file in self.daily_history[date]["files"]:
                    if file["status"] == status:
                        result.append(file)
        else:
            # За всю историю
            for day_data in self.daily_history.values():
                for file in day_data["files"]:
                    if file["status"] == status:
                        result.append(file)
        
        return result
    
    async def get_file_info(self, filename: str) -> Dict[str, Any]:
        """Получить информацию о конкретном файле (когда был обработан и т.д.)"""
        # Ищем файл во всей истории
        for day_data in self.daily_history.values():
            for file in day_data["files"]:
                if file["filename"] == filename:
                    return {
                        "found": True,
                        "file": file,
                        "date": day_data["date"]
                    }
        
        return {
            "found": False,
            "file": None,
            "message": f"File {filename} not found in history"
        }
    
    async def search_files(self, filename_pattern: str) -> List[Dict[str, Any]]:
        """Поиск файлов по шаблону имени"""
        result = []
        for day_data in self.daily_history.values():
            for file in day_data["files"]:
                if filename_pattern.lower() in file["filename"].lower():
                    result.append({
                        "date": day_data["date"],
                        "file": file
                    })
        return result
    
    async def get_summary(self) -> Dict[str, Any]:
        """Получить краткую сводку"""
        return {
            "session": {
                "processed": self.session_successful,
                "failed": self.session_failed
            },
            "all_time": {
                "processed": self.all_time_successful,
                "failed": self.all_time_failed
            }
        }
