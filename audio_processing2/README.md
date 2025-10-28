# 🎙️ Audio Processing System - Полное описание проекта

## 📋 Содержание

1. [Обзор проекта](#обзор-проекта)
2. [Архитектура системы](#архитектура-системы)
3. [Ключевые компоненты](#ключевые-компоненты)
4. [API документация](#api-документация)
5. [Конфигурация](#конфигурация)
6. [Установка и запуск](#установка-и-запуск)
7. [Примеры использования](#примеры-использования)
8. [Мониторинг и метрики](#мониторинг-и-метрики)
9. [Troubleshooting](#troubleshooting)

---

## 🎯 Обзор проекта

**Audio Processing System** — асинхронная система обработки аудиофайлов с автоматической транскрипцией речи в текст.

### Основные возможности:

✅ **Асинхронная обработка** — файлы обрабатываются в фоне через Job Queue  
✅ **Автоматический мониторинг** — отслеживание папки с аудиофайлами  
✅ **REST API** — полное управление через HTTP endpoints  
✅ **Масштабируемость** — настраиваемое количество рабочих потоков  
✅ **Метрики и статистика** — детальная информация о всех обработках  
✅ **Восстановление** — автоматическое восстановление после сбоев  
✅ **Web Dashboard** — React интерфейс для управления (опционально)

---

## 🏗️ Архитектура системы

```
┌──────────────────────────────────────────────────────────────┐
│                    AUDIO PROCESSING SYSTEM                   │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────┐      ┌────────────┐      ┌──────────────┐    │
│  │   Watcher  │─────▶│ Task Pool  │─────▶│Transcription│    │
│  │  (Monitor) │      │ (3 workers)│      │   Service    │    │
│  └────────────┘      └────────────┘      └──────────────┘    │
│        │                    │                    │           │
│        ▼                    ▼                    ▼           │
│  ┌──────────────────────────────────────────────────────┐    │
│  │           File Manager (Storage)                     │    │
│  │  uploads/ ──▶ processing/ ──▶ completed/            │    │
│  └──────────────────────────────────────────────────────┘    │
│                              │                               │
│                              ▼                               │
│  ┌──────────────────────────────────────────────────────┐    │
│  │        Metrics Collector (Statistics)                │    │
│  └──────────────────────────────────────────────────────┘    │
│                              │                               │
│                              ▼                               │
│  ┌──────────────────────────────────────────────────────┐    │
│  │         REST API (FastAPI + Uvicorn)                 │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                              │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  External API    │
                    │ (Transcription)  │
                    │ demo.connect2ai  │
                    └──────────────────┘
```

---

## 🔧 Ключевые компоненты

### 1. **Application Core** (`src/core/`)

Основной контроллер приложения, управляет жизненным циклом всех компонентов.

**Файлы:**
- `application.py` — главный класс приложения
- `exceptions.py` — пользовательские исключения

**Функции:**
- Инициализация всех сервисов
- Управление состоянием (running/paused/stopped)
- Graceful shutdown
- Восстановление после сбоев

---

### 2. **Transcription Service** (`src/services/transcription_service.py`)

Взаимодействие с внешним API для транскрипции аудио.

**Возможности:**
- ✅ Авторизация с автоматическими повторами
- ✅ Асинхронная отправка файлов (async=1)
- ✅ Polling статуса задачи
- ✅ Обработка ошибок и таймаутов
- ✅ Адаптивные таймауты

**API endpoints:**
```
POST /spr/stt              - Отправка файла (async=1)
GET  /spr/result/{taskID}  - Получение результата
```

**Статусы:**
- `ready` — результат готов
- `waiting` — обрабатывается
- `not found` — не найдена
- `failed` — ошибка

**Пример использования:**
```python
# Асинхронный режим
task_id = await service.submit_transcription_job(file_path)
result = await service.poll_transcription_result(task_id)

# Синхронный режим (для совместимости)
result = await service.transcribe_audio(file_path)
```

---

### 3. **Task Pool** (`src/services/task_pool.py`)

Пул рабочих потоков для параллельной обработки файлов.

**Параметры:**
- `max_workers: int` — количество одновременных задач (default: 3)
- `queue: asyncio.Queue` — очередь задач

**Возможности:**
- ✅ Динамическое изменение количества воркеров
- ✅ Graceful shutdown с завершением текущих задач
- ✅ Пауза/возобновление обработки
- ✅ Миграция файлов при перезапуске

**Жизненный цикл задачи:**
```
1. Файл добавлен в очередь
2. Воркер берет файл из очереди
3. Файл перемещается в processing/
4. Отправка на транскрипцию
5. Polling результата
6. Сохранение результата
7. Перемещение в completed/
8. Обновление метрик
```

---

### 4. **File Manager** (`src/services/file_manager.py`)

Управление файлами и папками.

**Структура папок:**
```
storage/
├── audio_uploads/    ← загруженные файлы (мониторится)
├── processing/       ← файлы в обработке
└── completed/        ← обработанные файлы
```

**Функции:**
- Проверка и создание папок
- Перемещение файлов между папками
- Сохранение результатов транскрипции
- Валидация размера файлов

**Поддерживаемые форматы:**
- MP3, WAV, M4A, FLAC, OGG, AAC

---

### 5. **Watcher** (`src/monitoring/watcher.py`)

Мониторинг папки `audio_uploads/` на наличие новых файлов.

**Параметры:**
- `scan_interval: float` — интервал сканирования (default: 2 сек)
- `watch_folder: str` — путь к папке

**Алгоритм:**
```python
while running:
    files = scan_folder()
    new_files = files - processed_files
    for file in new_files:
        task_pool.add_task(file)
    await asyncio.sleep(scan_interval)
```

---

### 6. **Metrics Collector** (`src/monitoring/metrics.py`)

Сбор статистики обработки файлов.

**Метрики:**

**Session (текущая сессия):**
- Успешно обработано
- Ошибок
- Время запуска
- Uptime

**All-time (вся история):**
- Всего успешных
- Всего ошибок
- Общий объем обработанных данных
- Среднее время обработки

**Хранение:**
```json
{
  "2025-10-27": {
    "successful": [
      {
        "filename": "audio_001.mp3",
        "timestamp": "2025-10-27T14:30:45.123456Z",
        "processing_time": 3.45,
        "size_bytes": 5242880
      }
    ],
    "failed": []
  }
}
```

**Файл:** `storage/metrics_history.json`

---

### 7. **REST API** (`src/api/`)

FastAPI приложение для управления системой.

**Endpoints:**

#### Статус
```
GET /status               - Общий статус приложения
GET /status/metrics       - Детальные метрики
```

#### Управление
```
POST /control/pause       - Пауза обработки
POST /control/resume      - Возобновление
POST /control/stop        - Остановка
```

#### Конфигурация
```
GET  /config              - Получить конфигурацию
PUT  /config              - Обновить конфигурацию
GET  /config/transcription
GET  /config/file_manager
GET  /config/api
```

#### Метрики
```
GET /status/metrics/files/last_days/{days}
GET /status/metrics/files/date/{date}
GET /status/metrics/files/status/{status}
GET /status/metrics/files/search?filename={pattern}
GET /status/metrics/files/info?filename={name}
GET /status/metrics/timeline?date={date}
```

#### Загрузка
```
POST /upload              - Загрузить аудиофайл
```

**Swagger UI:** `http://localhost:8000/docs`

---

## ⚙️ Конфигурация

### Основные параметры (`config/settings.py`)

```python
# Транскрипция
TRANSCRIPTION_ACCESS_TOKEN = "..."
LOGIN = "username"
PASSWORD = "password"
TRANSCRIPTION_SERVICE_URL = "https://demo.connect2ai.net/spr/stt"
AUTHORIZATION_SERVICE_URL = "https://demo.connect2ai.net/auth/login"

# Таймауты
TRANSCRIPTION_TIMEOUT = 300  # 5 минут
API_MAX_RETRIES = 5

# Task Pool
MAX_WORKERS = 3

# File Manager
UPLOAD_FOLDER = "storage/audio_uploads"
PROCESSING_FOLDER = "storage/processing"
COMPLETED_FOLDER = "storage/completed"
MAX_FILE_SIZE_MB = 100

# API
API_HOST = "0.0.0.0"
API_PORT = 8000

# Monitoring
SCAN_INTERVAL = 2.0
METRICS_ENABLED = True
HISTORY_RETENTION_DAYS = 30
```

### Динамическая конфигурация

Можно изменять через API без перезапуска:

```bash
curl -X PUT http://localhost:8000/config \
  -H "Content-Type: application/json" \
  -d '{
    "transcription": {
      "max_workers": 5,
      "max_file_size_mb": 200
    }
  }'
```

---

## 🚀 Установка и запуск

### Требования

- Python 3.8+
- pip / poetry

### Установка зависимостей

```bash
pip install -r requirements.txt
```

**Основные библиотеки:**
- `aiohttp` — асинхронные HTTP запросы
- `fastapi` — REST API
- `uvicorn` — ASGI сервер
- `structlog` — структурированное логирование
- `python-multipart` — загрузка файлов

### Настройка

1. Скопируйте `.env.example` в `.env`
2. Заполните credentials для API транскрипции
3. Создайте папки для хранения:
   ```bash
   mkdir -p storage/{audio_uploads,processing,completed}
   ```

### Запуск

**Только обработка файлов:**
```bash
python main.py
```

**С REST API:**
```bash
python main.py --api
```

---

## 📊 Примеры использования

### Сценарий 1: Автоматическая обработка

1. Запустить приложение:
   ```bash
   python main.py --api
   ```

2. Скопировать аудиофайл в `storage/audio_uploads/`

3. Приложение автоматически:
   - Обнаружит файл
   - Переместит в `processing/`
   - Отправит на транскрипцию
   - Получит результат
   - Сохранит в `completed/`

### Сценарий 2: Загрузка через API

```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@my_audio.mp3"
```

**Ответ:**
```json
{
  "success": true,
  "file": {
    "filename": "my_audio.mp3",
    "size_mb": 5.2,
    "upload_time": "2025-10-28T08:30:00Z"
  },
  "message": "File uploaded and queued for processing"
}
```

### Сценарий 3: Мониторинг статуса

```bash
curl http://localhost:8000/status
```

**Ответ:**
```json
{
  "status": "running",
  "uptime_seconds": 3600,
  "tasks": {
    "active_workers": 3,
    "queue_size": 5,
    "processing": 2
  },
  "metrics": {
    "session_successful": 145,
    "all_time_successful": 1250
  }
}
```

### Сценарий 4: Изменение конфигурации

```bash
# Увеличить количество воркеров
curl -X PUT http://localhost:8000/config \
  -H "Content-Type: application/json" \
  -d '{"transcription": {"max_workers": 5}}'

# Изменить максимальный размер файла
curl -X PUT http://localhost:8000/config \
  -H "Content-Type: application/json" \
  -d '{"transcription": {"max_file_size_mb": 200}}'
```

### Сценарий 5: Получение метрик

```bash
# Файлы за последние 7 дней
curl http://localhost:8000/status/metrics/files/last_days/7

# Файлы за конкретную дату
curl http://localhost:8000/status/metrics/files/date/2025-10-27

# Поиск файла
curl http://localhost:8000/status/metrics/files/search?filename=audio
```

---

## 📈 Мониторинг и метрики

### Логирование

**Уровни логов:**
- `DEBUG` — детальная информация
- `INFO` — основные события
- `WARNING` — предупреждения
- `ERROR` — ошибки

**Формат:**
```
2025-10-28T08:30:45.123456Z [info] event.name [component] key1=value1 key2=value2
```

**Примеры:**
```
✅ authentication.successful [transcription_service] token_prefix=eyJh...
✅ task.processing.file [task_pool] file=audio.mp3 task_id=0
✅ transcription.polling.completed [transcription_service] task_id=123 attempt=5
❌ transcription.polling.error [transcription_service] error="timeout"
```

### Метрики в реальном времени

**Dashboard endpoint:**
```
GET /status
```

**Ключевые метрики:**
- Uptime
- Активных воркеров
- Размер очереди
- Файлов в обработке
- Успешных/неудачных обработок
- Средняя скорость обработки

### Файл истории

**Расположение:** `storage/metrics_history.json`

**Структура:**
```json
{
  "2025-10-28": {
    "successful": [...],
    "failed": [...]
  }
}
```

**Retention:** 30 дней (настраивается)

---

## 🔍 Troubleshooting

### Проблема: Файлы не обрабатываются

**Симптомы:**
```
✅ watcher.started
❌ task.pool не берет файлы
```

**Решения:**
1. Проверить права на папки
2. Проверить формат файла (должен быть mp3/wav/etc)
3. Проверить размер файла (< MAX_FILE_SIZE_MB)
4. Посмотреть логи: `task.pool.stopping`

### Проблема: Ошибка авторизации

**Симптомы:**
```
❌ authentication.failed [status_code=401]
```

**Решения:**
1. Проверить LOGIN и PASSWORD в `.env`
2. Проверить доступность `AUTHORIZATION_SERVICE_URL`
3. Проверить таймауты (увеличить `auth_timeout`)

### Проблема: Таймаут при polling

**Симптомы:**
```
❌ transcription.polling.timeout [max_attempts=30]
```

**Решения:**
1. Увеличить `max_polling_attempts`:
   ```python
   PUT /config
   {"transcription": {"max_polling_attempts": 600}}
   ```
2. Уменьшить `polling_interval` (чаще проверять)
3. Проверить статус задачи вручную:
   ```
   GET /spr/result/{taskID}
   ```

### Проблема: Server disconnected

**Симптомы:**
```
❌ transcription.async_job.submission.error error='Server disconnected'
```

**Решения:**
1. Проверить доступность API:
   ```bash
   ping demo.connect2ai.net
   curl https://demo.connect2ai.net/spr/stt
   ```
2. Увеличить таймауты:
   ```python
   PUT /config
   {
     "transcription": {
       "connection_timeout_seconds": 30,
       "timeout_seconds": 600
     }
   }
   ```
3. Проверить firewall/proxy

### Проблема: Файлы зависают в processing/

**Симптомы:**
- Файлы не перемещаются в completed/
- Логов нет

**Решения:**
1. Перезапустить приложение (файлы вернутся в uploads/)
2. Проверить логи последних задач
3. Проверить статус задачи через API:
   ```
   GET /status/metrics/files/info?filename=stuck_file.mp3
   ```

---

## 🛠️ Разработка

### Структура проекта

```
audio_processing2/
├── config/
│   └── settings.py           # Конфигурация
├── src/
│   ├── api/
│   │   ├── main.py           # FastAPI app
│   │   └── routes.py         # API endpoints
│   ├── core/
│   │   ├── application.py    # Main app
│   │   └── exceptions.py     # Custom exceptions
│   ├── services/
│   │   ├── transcription_service.py
│   │   ├── task_pool.py
│   │   └── file_manager.py
│   └── monitoring/
│       ├── watcher.py
│       └── metrics.py
├── storage/
│   ├── audio_uploads/
│   ├── processing/
│   ├── completed/
│   └── metrics_history.json
├── main.py                   # Entry point
├── requirements.txt
└── README.md
```

### Добавление новых функций

**Пример: Добавить новый endpoint**

1. Создать роут в `src/api/routes.py`:
```python
@router.get("/new_endpoint")
async def new_endpoint():
    return {"message": "Hello"}
```

2. Перезапустить API

**Пример: Изменить логику обработки**

1. Отредактировать `src/services/task_pool.py`
2. Добавить логирование
3. Протестировать

---

## 📚 Дополнительная документация

- [React Web App Specification](react-web-app-spec.md) — ТЗ для фронтенд разработчика
- [Config API Documentation](react-web-app-config-api.md) — API конфигурирования
- [Transcription Service](transcription-service-correct-api.py) — Исходный код сервиса

---

## 📞 Контакты и поддержка

**Проект:** Audio Processing System  
**Версия:** 2.0  
**Дата:** October 2025

**Технологии:**
- Python 3.8+
- AsyncIO
- FastAPI
- aiohttp
- structlog

---

## 📝 Лицензия

MIT License

---

**Готово к использованию!** 🚀
