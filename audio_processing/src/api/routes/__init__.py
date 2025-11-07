"""
API маршруты для конфигурирования приложения в реальном времени.
Поддержка получения и изменения параметров без перезапуска.
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger()

# Глобальная ссылка на приложение
_app_instance = None


def set_app(app):
    """Установить экземпляр приложения"""
    global _app_instance
    _app_instance = app


def get_app():
    """Получить экземпляр приложения"""
    if _app_instance is None:
        raise HTTPException(status_code=503, detail="Application not initialized")
    return _app_instance


# ========== PYDANTIC MODELS ==========

class ControlRequest(BaseModel):
    """Запрос на управление"""
    action: str  # start, stop, pause, resume, restart


class ControlResponse(BaseModel):
    """Ответ управления"""
    success: bool
    message: str
    timestamp: datetime


class ConfigUpdate(BaseModel):
    """Обновление конфигурации приложения"""
    max_concurrent_tasks: Optional[int] = Field(
        None, ge=1, le=20, description="Количество одновременных задач"
    )
    max_file_size_bytes: Optional[int] = Field(
        None, ge=1024*1024, description="Максимальный размер файла (байты)"
    )
    max_transcription_calls: Optional[int] = Field(
        None, ge=1, le=10, description="Макс одновременных запросов транскрипции"
    )
    max_api_calls: Optional[int] = Field(
        None, ge=1, le=20, description="Макс одновременных API вызовов"
    )
    task_queue_max_size: Optional[int] = Field(
        None, ge=10, le=1000, description="Максимальный размер очереди"
    )
    queue_check_interval: Optional[int] = Field(
        None, ge=1, le=60, description="Интервал сканирования папки (сек)"
    )


class ConfigResponse(BaseModel):
    """Ответ с конфигурацией"""
    max_concurrent_tasks: int
    max_file_size_bytes: int
    max_transcription_calls: int
    max_api_calls: int
    task_queue_max_size: int
    queue_check_interval: int


class ConfigUpdateResponse(BaseModel):
    """Ответ обновления конфигурации"""
    status: str
    updated: Dict[str, Any]
    current: ConfigResponse
    message: str


# ========== ROUTES ==========

def setup_routes(app: FastAPI, application_instance):
    """Подключить все роуты к FastAPI приложению"""
    
    set_app(application_instance)
    
    # ========== HEALTH & STATUS ==========
    
    @app.get("/health")
    async def health_check() -> Dict[str, Any]:
        """Проверка здоровья сервиса"""
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "service": "audio-processing"
        }
    
    @app.get("/status")
    async def get_status() -> Dict[str, Any]:
        """Получить полный статус приложения"""
        app_inst = get_app()
        return await app_inst.get_status()
    
    @app.get("/status/queue")
    async def get_queue_status() -> Dict[str, Any]:
        """Получить статус очереди"""
        app_inst = get_app()
        status = await app_inst.get_status()
        task_status = status.get("task_pool_status", {})
        return {
            "queue_size": task_status.get("queue_size", 0),
            "queue_max_size": task_status.get("queue_max_size", 0),
            "processed_total": task_status.get("processed_total", 0),
            "failed_total": task_status.get("failed_total", 0),
            "success_rate": task_status.get("success_rate", 0)
        }
    
    # ========== CONTROL ==========
    
    @app.post("/control", response_model=ControlResponse)
    async def control_application(request: ControlRequest) -> ControlResponse:
        """Управление состоянием приложения"""
        app_inst = get_app()
        action = request.action.lower()
        
        try:
            if action == "start":
                await app_inst.start()
                message = "Application started"
            elif action == "stop":
                await app_inst.stop()
                message = "Application stopped"
            elif action == "pause":
                await app_inst.pause()
                message = "Application paused"
            elif action == "resume":
                await app_inst.resume()
                message = "Application resumed"
            elif action == "restart":
                await app_inst.restart()
                message = "Application restarted"
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unknown action: {action}"
                )
            
            logger.info("control.action.success", action=action)
            return ControlResponse(
                success=True,
                message=message,
                timestamp=datetime.now()
            )
        
        except Exception as e:
            logger.error("control.action.failed", action=action, error=str(e))
            return ControlResponse(
                success=False,
                message=f"Error: {str(e)}",
                timestamp=datetime.now()
            )
    
    # ========== CONFIGURATION ==========
    
    @app.get("/config", response_model=ConfigResponse)
    async def get_config() -> ConfigResponse:
        """Получить текущую конфигурацию"""
        from config.settings import settings
        return ConfigResponse(
            max_concurrent_tasks=settings.MAX_CONCURRENT_TASKS,
            max_file_size_bytes=settings.MAX_FILE_SIZE_BYTES,
            max_transcription_calls=settings.MAX_TRANSCRIPTION_CALLS,
            max_api_calls=settings.MAX_API_CALLS,
            task_queue_max_size=settings.TASK_QUEUE_MAX_SIZE,
            queue_check_interval=settings.QUEUE_CHECK_INTERVAL
        )
    
    @app.post("/config", response_model=ConfigUpdateResponse)
    async def update_config(config_update: ConfigUpdate) -> ConfigUpdateResponse:
        """
        Обновить конфигурацию приложения (hot-reload).
        
        Изменения вступают в силу немедленно без перезапуска.
        """
        from config.settings import settings
        app_inst = get_app()
        
        try:
            updated = {}
            
            # Обновляем параметры в settings
            if config_update.max_concurrent_tasks is not None:
                settings.MAX_CONCURRENT_TASKS = config_update.max_concurrent_tasks
                updated["max_concurrent_tasks"] = config_update.max_concurrent_tasks
                logger.info("config.updated", param="max_concurrent_tasks", 
                           value=config_update.max_concurrent_tasks)
            
            if config_update.max_file_size_bytes is not None:
                settings.MAX_FILE_SIZE_BYTES = config_update.max_file_size_bytes
                updated["max_file_size_bytes"] = config_update.max_file_size_bytes
                logger.info("config.updated", param="max_file_size_bytes",
                           value=config_update.max_file_size_bytes)
            
            if config_update.max_transcription_calls is not None:
                settings.MAX_TRANSCRIPTION_CALLS = config_update.max_transcription_calls
                updated["max_transcription_calls"] = config_update.max_transcription_calls
                logger.info("config.updated", param="max_transcription_calls",
                           value=config_update.max_transcription_calls)
            
            if config_update.max_api_calls is not None:
                settings.MAX_API_CALLS = config_update.max_api_calls
                updated["max_api_calls"] = config_update.max_api_calls
                logger.info("config.updated", param="max_api_calls",
                           value=config_update.max_api_calls)
            
            if config_update.task_queue_max_size is not None:
                settings.TASK_QUEUE_MAX_SIZE = config_update.task_queue_max_size
                updated["task_queue_max_size"] = config_update.task_queue_max_size
                logger.info("config.updated", param="task_queue_max_size",
                           value=config_update.task_queue_max_size)
            
            if config_update.queue_check_interval is not None:
                settings.QUEUE_CHECK_INTERVAL = config_update.queue_check_interval
                updated["queue_check_interval"] = config_update.queue_check_interval
                logger.info("config.updated", param="queue_check_interval",
                           value=config_update.queue_check_interval)
            
            # Если изменилось количество concurrent tasks, нужно пересоздать TaskPool
            if config_update.max_concurrent_tasks is not None:
                logger.info("config.applying.task_pool_reload")
                await app_inst.restart_task_pool()
                logger.info("config.task_pool_reloaded")
            
            # Получить текущую конфигурацию для ответа
            current_config = ConfigResponse(
                max_concurrent_tasks=settings.MAX_CONCURRENT_TASKS,
                max_file_size_bytes=settings.MAX_FILE_SIZE_BYTES,
                max_transcription_calls=settings.MAX_TRANSCRIPTION_CALLS,
                max_api_calls=settings.MAX_API_CALLS,
                task_queue_max_size=settings.TASK_QUEUE_MAX_SIZE,
                queue_check_interval=settings.QUEUE_CHECK_INTERVAL
            )
            
            message = f"Successfully updated {len(updated)} parameter(s)"
            logger.info("config.update.success", count=len(updated))
            
            return ConfigUpdateResponse(
                status="success",
                updated=updated,
                current=current_config,
                message=message
            )
        
        except ValueError as e:
            logger.error("config.validation.error", error=str(e))
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error("config.update.failed", error=str(e))
            raise HTTPException(status_code=500, detail=str(e))
    


    # ========== METRICS ==========
    
    @app.get("/status/metrics")
    async def get_metrics() -> Dict[str, Any]:
        """
        Получить расширенные метрики с историей.
        
        Включает:
        - current_session: метрики текущей сессии
        - all_time: метрики за всю историю
        - daily: ежедневная статистика
        """
        app_inst = get_app()
        if not app_inst.metrics:
            raise HTTPException(status_code=503, detail="Metrics not available")
        
        metrics = await app_inst.metrics.get_metrics()
        logger.info("metrics.retrieved", endpoint="/status/metrics")
        return metrics


    @app.get("/status/metrics/session")
    async def get_session_metrics() -> Dict[str, Any]:
        """Получить метрики только текущей сессии"""
        app_inst = get_app()
        if not app_inst.metrics:
            raise HTTPException(status_code=503, detail="Metrics not available")
        
        metrics = await app_inst.metrics.get_metrics()
        return {
            "current_session": metrics["current_session"]
        }


    @app.get("/status/metrics/all_time")
    async def get_all_time_metrics() -> Dict[str, Any]:
        """Получить метрики за всю историю"""
        app_inst = get_app()
        if not app_inst.metrics:
            raise HTTPException(status_code=503, detail="Metrics not available")
        
        metrics = await app_inst.metrics.get_metrics()
        return {
            "all_time": metrics["all_time"]
        }


    @app.get("/status/metrics/daily")
    async def get_daily_metrics() -> Dict[str, Any]:
        """Получить ежедневную статистику"""
        app_inst = get_app()
        if not app_inst.metrics:
            raise HTTPException(status_code=503, detail="Metrics not available")
        
        metrics = await app_inst.metrics.get_metrics()
        return {
            "daily": metrics["daily"]
        }


    @app.get("/status/metrics/summary")
    async def get_metrics_summary() -> Dict[str, Any]:
        """Получить краткую сводку метрик"""
        app_inst = get_app()
        if not app_inst.metrics:
            raise HTTPException(status_code=503, detail="Metrics not available")
        
        summary = await app_inst.metrics.get_summary()
        logger.info("metrics.summary.retrieved")
        return summary


    @app.get("/status/metrics/compare")
    async def compare_metrics() -> Dict[str, Any]:
        """Сравнение метрик текущей сессии и всей истории"""
        app_inst = get_app()
        if not app_inst.metrics:
            raise HTTPException(status_code=503, detail="Metrics not available")
        
        metrics = await app_inst.metrics.get_metrics()
        
        session = metrics["current_session"]
        all_time = metrics["all_time"]
        
        return {
            "comparison": {
                "session_vs_all_time": {
                    "session_successful": session["successful"],
                    "all_time_successful": all_time["successful"],
                    "difference": all_time["successful"] - session["successful"],
                    "session_success_rate": session["success_rate"],
                    "all_time_success_rate": all_time["success_rate"],
                    "rate_difference": all_time["success_rate"] - session["success_rate"]
                },
                "session": {
                    "processed": session["successful"],
                    "failed": session["failed"],
                    "success_rate": session["success_rate"],
                    "uptime": session["uptime"]
                },
                "all_time": {
                    "processed": all_time["successful"],
                    "failed": all_time["failed"],
                    "success_rate": all_time["success_rate"],
                    "uptime": all_time["uptime"]
                },
                "today": metrics["daily"]["today"]
            }
        }

    @app.get("/status/metrics/files/date/{date}")
    async def get_files_by_date(date: str) -> Dict[str, Any]:
        """
        Получить все файлы, обработанные в конкретный день.
        
        Параметры:
        - date: дата в формате YYYY-MM-DD (например, 2025-10-27)
        
        Пример:
        GET /status/metrics/files/date/2025-10-27
        """
        app_inst = get_app()
        if not app_inst.metrics:
            raise HTTPException(status_code=503, detail="Metrics not available")
        
        try:
            # Валидируем формат даты
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail="Invalid date format. Use YYYY-MM-DD (e.g., 2025-10-27)"
            )
        
        files = await app_inst.metrics.get_files_by_date(date)
        
        logger.info("files.retrieved.by_date", date=date, count=len(files))
        return {
            "date": date,
            "count": len(files),
            "files": files
        }


    @app.get("/status/metrics/files/last_days/{days}")
    async def get_files_last_days(days: int) -> Dict[str, Any]:
        """
        Получить все файлы за последние N дней.
        
        Параметры:
        - days: количество дней (например, 7)
        
        Пример:
        GET /status/metrics/files/last_days/7  (за неделю)
        GET /status/metrics/files/last_days/30 (за месяц)
        """
        if days < 1 or days > 365:
            raise HTTPException(
                status_code=400,
                detail="Days must be between 1 and 365"
            )
        
        app_inst = get_app()
        if not app_inst.metrics:
            raise HTTPException(status_code=503, detail="Metrics not available")
        
        files = await app_inst.metrics.get_files_from_last_n_days(days)
        
        logger.info("files.retrieved.last_days", days=days, count=len(files))
        return {
            "period": f"last {days} days",
            "count": len(files),
            "files": files
        }


    @app.get("/status/metrics/files/status/{status}")
    async def get_files_by_status(status: str, date: str = None) -> Dict[str, Any]:
        """
        Получить файлы по статусу (успешные или ошибки).
        
        Параметры:
        - status: "success" или "failed"
        - date (опционально): конкретная дата (YYYY-MM-DD)
        
        Примеры:
        GET /status/metrics/files/status/success           (все успешные файлы)
        GET /status/metrics/files/status/failed            (все ошибки)
        GET /status/metrics/files/status/success?date=2025-10-27  (успешные за день)
        """
        if status not in ["success", "failed"]:
            raise HTTPException(
                status_code=400,
                detail="Status must be 'success' or 'failed'"
            )
        
        if date:
            try:
                datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid date format. Use YYYY-MM-DD"
                )
        
        app_inst = get_app()
        if not app_inst.metrics:
            raise HTTPException(status_code=503, detail="Metrics not available")
        
        files = await app_inst.metrics.get_files_by_status(status, date)
        
        logger.info("files.retrieved.by_status", status=status, date=date, count=len(files))
        return {
            "status": status,
            "date": date or "all_time",
            "count": len(files),
            "files": files
        }


    @app.get("/status/metrics/files/search")
    async def search_files(filename: str) -> Dict[str, Any]:
        """
        Поиск файла по имени (частичное совпадение).
        
        Параметры:
        - filename: часть имени файла
        
        Пример:
        GET /status/metrics/files/search?filename=audio
        """
        if not filename or len(filename) < 1:
            raise HTTPException(
                status_code=400,
                detail="Filename must be at least 1 character"
            )
        
        app_inst = get_app()
        if not app_inst.metrics:
            raise HTTPException(status_code=503, detail="Metrics not available")
        
        results = await app_inst.metrics.search_files(filename)
        
        logger.info("files.searched", pattern=filename, count=len(results))
        return {
            "pattern": filename,
            "count": len(results),
            "results": results
        }


    @app.get("/status/metrics/files/info")
    async def get_file_info(filename: str) -> Dict[str, Any]:
        """
        Получить детальную информацию о конкретном файле.
        
        Параметры:
        - filename: точное имя файла
        
        Пример:
        GET /status/metrics/files/info?filename=audio_001.mp3
        """
        if not filename:
            raise HTTPException(
                status_code=400,
                detail="Filename is required"
            )
        
        app_inst = get_app()
        if not app_inst.metrics:
            raise HTTPException(status_code=503, detail="Metrics not available")
        
        info = await app_inst.metrics.get_file_info(filename)
        
        if not info["found"]:
            logger.warning("file.not_found", filename=filename)
            raise HTTPException(
                status_code=404,
                detail=f"File '{filename}' not found in history"
            )
        
        logger.info("file.info.retrieved", filename=filename)
        return {
            "found": True,
            "date": info["date"],
            "file": info["file"]
        }


    @app.get("/status/metrics/timeline")
    async def get_processing_timeline(date: str = None) -> Dict[str, Any]:
        """
        Получить временную шкалу обработки файлов.
        
        Показывает когда каждый файл был обработан с сортировкой по времени.
        
        Параметры:
        - date (опционально): конкретная дата (YYYY-MM-DD)
        
        Пример:
        GET /status/metrics/timeline
        GET /status/metrics/timeline?date=2025-10-27
        """
        app_inst = get_app()
        if not app_inst.metrics:
            raise HTTPException(status_code=503, detail="Metrics not available")
        
        if date:
            try:
                datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid date format. Use YYYY-MM-DD"
                )
            
            files = await app_inst.metrics.get_files_by_date(date)
        else:
            # За последние 7 дней по умолчанию
            files = await app_inst.metrics.get_files_from_last_n_days(7)
        
        # Сортируем по времени обработки
        files_sorted = sorted(
            files, 
            key=lambda x: x["timestamp"], 
            reverse=True
        )
        
        logger.info("timeline.retrieved", date=date or "last_7_days", count=len(files_sorted))
        return {
            "period": date or "last 7 days",
            "count": len(files_sorted),
            "timeline": files_sorted
        }

    logger.info("routes.configured")
