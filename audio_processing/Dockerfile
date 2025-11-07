FROM python:3.11-slim

# Ускоряем pip, ставим system deps
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Установка зависимостей (system deps и wheel для ускорения установки)
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc build-essential && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем только requirements для кэширования слоев
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем весь код
COPY . .

# (Не обязательно, но если у вас есть .env файл или директория конфигов:)
# COPY .env ./

# Открываем порт приложения (FastAPI обычно 8000)
EXPOSE 8000

# Жестко фиксируем encoding для журналов/логов
ENV PYTHONIOENCODING=UTF-8

# Основной запуск (при необходимости ключи можно изменить)
CMD ["python", "main.py", "--api"]

# Для отладки используйте (раскомментируйте при необходимости):
# CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
