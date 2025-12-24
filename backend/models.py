from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from database import Base


class User(Base):
    """Модель пользователя для авторизации"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Conversation(Base):
    """Модель разговора"""
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    file_data = Column(JSONB, nullable=True)
    file_name = Column(String(64), nullable=False)
    file_path = Column(String(255), nullable=False)
    date_time = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

