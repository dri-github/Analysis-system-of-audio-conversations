# Audio Processing System

Система для автоматической обработки аудиофайлов с транскрипцией и интеграцией с внешними API.

---

## 🚀 Возможности

- **Автоматический мониторинг** папки на появление новых аудиофайлов  
- **Параллельная обработка** нескольких файлов одновременно  
- **Транскрипция аудио** через внешний сервис Connect2AI  
- **Сохранение результатов** в JSON формате  
- **Интеграция с API** для отправки результатов  
- **Структурированное логирование** с разделением по компонентам  
- **Обработка ошибок** с повторными попытками  

---

## 🛠 Технологии

- **Python 3.8+**  
- **Requests** — HTTP-запросы  
- **Structlog** — структурированное логирование  
- **Watchdog** — мониторинг файловой системы  
- **Threading** — многопоточная обработка  

---

## 📦 Установка

1. **Клонируйте репозиторий:**
   ```bash
   git clone <repository-url>
   cd audio_processing
2. **Установите зависимости:**

    ```bash
    pip install -r requirements.txt
3. **Настройте переменные окружения(cоздайте файл .env в корне проекта):**
    ```bash
    # Настройки папок
    WATCH_FOLDER=./audio_uploads
    PROCESSING_FOLDER=./processing
    PROCESSED_FOLDER=./processed
    JSON_FOLDER=./json_output

    # Настройки авторизации транскрипции
    LOGIN=your_username
    PASSWORD=your_password
    AUTORIZATION_SERVICE_URL=https://demo.connect2ai.net/spr/auth/signin

    # Настройки API
    BACKEND_API=http://your-api-server.com/api
    API_ENDPOINT=http://your-api-server.com/api/conversations

    # Настройки системы
    MAX_WORKERS=3
    QUEUE_CHECK_INTERVAL=2
    LOG_LEVEL=INFO
---
## 🎯 Использование
**Запуск системы:**

```bash
python main.py
```
Структура папок:

```bash
audio_processing/
├── audio_uploads/      # Входящие аудиофайлы
├── processing/         # Файлы в обработке
├── processed/          # Обработанные аудиофайлы
├── json_output/        # JSON результаты транскрипции
└── logs/               # Логи системы
```
Поддерживаемые форматы:
WAV, MP3, M4A, FLAC, OGG

## ⚙️ Конфигурация
Основные настройки в config.py:

```python
# Количество параллельных воркеров
MAX_WORKERS = 3

# Таймауты (секунды)
TRANSCRIPTION_TIMEOUT = 300
API_TIMEOUT = 30

# Повторные попытки
MAX_RETRIES = 3
API_MAX_RETRIES = 3
```
---
## 📊 Логирование
*Система использует структурированное логирование.*

**Файлы логов:**

```bash
Копировать код
logs/
├── main.log                 # Главный модуль
├── folder_watcher.log       # Мониторинг папки
├── worker_manager.log       # Управление воркерами
├── transcription_worker.log # Транскрипция
└── worker_{n}.log           # Логи отдельных воркеров
```
**Уровни логирования:**
```
INFO — основная информация
DEBUG — детальная отладка
WARNING — предупреждения
ERROR — ошибки
```
---
## 🔧 Архитектура
**Компоненты системы:**

*Folder Watcher — мониторинг папки audio_uploads*

*Worker Manager — управление пулом воркеров*

*Transcription Worker — обработка транскрипции*

*API Client — отправка результатов*

**Поток данных:**

Аудиофайл → Folder Watcher → Очередь → Worker → Транскрипция → JSON + API

---
## 🐛 Отладка
**Включение детального логирования:**

```bash
LOG_LEVEL=DEBUG
```
**Проверка статуса системы:**

В логах ищите сообщения system_status для мониторинга очереди и воркеров.

**Типичные проблемы:**

- Нет доступа к папкам — проверьте права

- Ошибки авторизации — проверьте LOGIN/PASSWORD в .env

- API недоступно — проверьте настройки API_ENDPOINT

---
## 📈 Мониторинг

**Система предоставляет метрики:**

- Размер очереди обработки

- Статус воркеров (свободны/заняты)

- Количество обработанных файлов

- Уровень утилизации воркеров

---
## 🤝 Разработка
**Требования:**

- Python 3.8+

- Установленные зависимости из requirements.txt

**Запуск тестов:**

```bash
# Добавьте тестовые файлы в audio_uploads/
cp test_audio.wav audio_uploads/
```
**Структура проекта:**

```
Копировать код
src/
├── main.py
├── config.py
├── worker_manager.py
├── logging_config.py
├── monitor/
│   └── folder_watcher.py
└── workers/
    └── transcription_worker.py
```
## 📄 Версия
***Version 0.2***

## 👥 Авторы
***Дробушевич Егор Вячеславович***

