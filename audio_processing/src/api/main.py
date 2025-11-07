"""
FastAPI приложение для управления обработкой аудио.
Упрощенная структура с разделенными роутами.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import structlog

logger = structlog.get_logger()


def create_app(application_instance) -> FastAPI:
    """
    Создать FastAPI приложение.
    
    Args:
        application_instance: Экземпляр AudioProcessingApplication
    
    Returns:
        Настроенное FastAPI приложение
    """
    
    app = FastAPI(
        title="Audio Processing API",
        description="API для управления обработкой аудиофайлов",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )
    
    # Подключить роуты
    from src.api.routes import setup_routes
    setup_routes(app, application_instance)
    
    # Главная страница
    @app.get("/", response_class=HTMLResponse)
    async def root():
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Audio Processing API</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
                h1 { color: #333; }
                .endpoint { background: #f4f4f4; padding: 10px; margin: 10px 0; border-radius: 5px; }
                a { color: #0066cc; text-decoration: none; }
                a:hover { text-decoration: underline; }
            </style>
        </head>
        <body>
            <h1>🎵 Audio Processing API</h1>
            <p>API для автоматической обработки и транскрипции аудиофайлов</p>
            
            <h2>Доступные эндпоинты:</h2>
            
            <div class="endpoint">
                <strong>GET /health</strong> - Проверка здоровья сервиса
            </div>
            
            <div class="endpoint">
                <strong>GET /status</strong> - Полный статус приложения
            </div>
            
            <div class="endpoint">
                <strong>POST /control</strong> - Управление (start/stop/pause/resume)
            </div>
            
            <h2>Документация:</h2>
            <ul>
                <li><a href="/docs">Swagger UI</a> - Интерактивная документация</li>
                <li><a href="/redoc">ReDoc</a> - Альтернативная документация</li>
            </ul>
        </body>
        </html>
        """
    
    logger.info("fastapi.app.created")
    return app
