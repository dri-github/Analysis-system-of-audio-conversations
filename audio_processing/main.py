#!/usr/bin/env python3
"""
Главный файл запуска приложения.
Упрощенная версия без sys.path манипуляций.
"""
import asyncio
import signal
import argparse
from typing import Optional
import structlog

from config.logging_config import setup_logging
from src.core.application import AudioProcessingApplication

logger = structlog.get_logger()


class ApplicationRunner:
    """Запуск и управление приложением"""
    
    def __init__(self):
        self.app: Optional[AudioProcessingApplication] = None
        self.is_running = True

    async def run_application(self, enable_api: bool = False) -> None:
        """
        Запуск приложения.
        
        Args:
            enable_api: Запустить FastAPI веб-интерфейс
        """
        try:
            # Настройка логирования
            logger = setup_logging()
            
            # Создаем приложение
            self.app = AudioProcessingApplication()
            
            # Обработчик сигналов
            def signal_handler(signum, frame):
                logger.info("signal.received", signal=signum)
                self.is_running = False
                asyncio.create_task(self._shutdown())
            
            # Регистрируем обработчики сигналов
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            
            # Запускаем приложение
            await self.app.start()
            logger.info("application.started.successfully")
            print("✅ Application started successfully!")
            print("📁 Monitoring folder: storage/audio_uploads")
            print("🎯 Press Ctrl+C to stop")
            
            # Если нужен API
            if enable_api:
                await self._start_api()
            
            # Главный цикл
            while self.is_running:
                await asyncio.sleep(1)
            
        except KeyboardInterrupt:
            logger.info("keyboard.interrupt")
        except Exception as e:
            logger.error("application.error", error=str(e))
            raise
        finally:
            await self._shutdown()

    async def _start_api(self) -> None:
        """Запуск FastAPI сервера"""
        try:
            import uvicorn
            from src.api.main import create_app
            
            app = create_app(self.app)
            
            config = uvicorn.Config(
                app,
                host="0.0.0.0",
                port=8000,
                log_level="info"
            )
            server = uvicorn.Server(config)
            
            logger.info("api.server.starting", port=8000)
            print("🌐 API Server: http://localhost:8000")
            print("📖 API Docs: http://localhost:8000/docs")
            
            # Запускаем сервер в отдельной задаче
            asyncio.create_task(server.serve())
            
        except ImportError:
            logger.warning("api.dependencies.missing", 
                         message="Install with: pip install fastapi uvicorn")
        except Exception as e:
            logger.error("api.start.failed", error=str(e))

    async def _shutdown(self) -> None:
        """Graceful shutdown приложения"""
        if self.app:
            logger.info("application.shutting.down")
            try:
                await self.app.stop()
                logger.info("application.shutdown.complete")
            except Exception as e:
                logger.error("application.shutdown.error", error=str(e))


def main():
    """Главная функция"""
    parser = argparse.ArgumentParser(
        description="Audio Processing Application"
    )
    parser.add_argument(
        "--api",
        action="store_true",
        help="Enable FastAPI web interface"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Set logging level"
    )
    
    args = parser.parse_args()
    
    # Запускаем приложение
    runner = ApplicationRunner()
    
    try:
        asyncio.run(runner.run_application(enable_api=args.api))
    except KeyboardInterrupt:
        print("\n👋 Application stopped")
    except Exception as e:
        print(f"❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
