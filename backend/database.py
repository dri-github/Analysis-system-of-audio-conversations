from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

# URL подключения к БД
DATABASE_URL = "postgresql://audrec_conv_s:service@postgres:5432/audio_rec"

# Создание движка SQLAlchemy
engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,  # Для async операций
    echo=False  # Установите True для отладки SQL запросов
)

# Создание фабрики сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Базовый класс для моделей
Base = declarative_base()


# Dependency для получения сессии БД
def get_db():
    """Генератор сессии БД для использования в FastAPI dependencies"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

