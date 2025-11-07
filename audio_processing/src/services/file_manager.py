"""
Менеджер файлов с поддержкой MinIO и локального хранилища.
"""

import json
from pathlib import Path
from typing import Optional, List, Dict, Any

import structlog
from config.settings import settings
from src.core.exceptions import FileManagementError
from src.storage.storage_manager import StorageManager

logger = structlog.get_logger()


class FileManager:
    """Управление файлами и папками приложения с поддержкой MinIO"""

    def __init__(self, storage_manager: StorageManager):
        """Инициализация менеджера файлов"""
        self.storage = storage_manager
        self._ensure_buckets()

    def _ensure_buckets(self) -> None:
        """Убедиться что все необходимые buckets созданы (для локального хранилища)"""
        try:
            if not settings.USE_MINIO:
                # Для локального хранилища создаём директории
                buckets = [
                    settings.UPLOAD_DIR,
                    settings.PROCESSING_DIR,
                    settings.PROCESSED_DIR,
                    settings.JSON_OUTPUT_DIR,
                ]
                for bucket in buckets:
                    Path(bucket).mkdir(parents=True, exist_ok=True)
                logger.info("directories.verified")
            logger.info("buckets.verified")
        except Exception as e:
            raise FileManagementError(f"Failed to ensure buckets: {e}")

    async def initialize_minio_buckets(self) -> None:
        """Инициализация buckets в MinIO (вызывается при старте приложения)"""
        if not settings.USE_MINIO:
            return

        try:
            buckets = [
                settings.MINIO_UPLOADS_BUCKET,
                settings.MINIO_PROCESSING_BUCKET,
                settings.MINIO_PROCESSED_BUCKET,
                settings.MINIO_JSON_OUTPUT_BUCKET,
            ]

            for bucket in buckets:
                await self.storage.create_bucket_if_not_exists(bucket)
                logger.info("bucket.initialized", bucket=bucket)
        except Exception as e:
            logger.error("bucket.initialization.failed", error=str(e))
            raise

    def _get_bucket_name(self, bucket_type: str) -> str:
        """Получение имени bucket в зависимости от типа и конфигурации"""
        if settings.USE_MINIO:
            bucket_map = {
                "upload": settings.MINIO_UPLOADS_BUCKET,
                "processing": settings.MINIO_PROCESSING_BUCKET,
                "processed": settings.MINIO_PROCESSED_BUCKET,
                "json": settings.MINIO_JSON_OUTPUT_BUCKET,
            }
            return bucket_map.get(bucket_type, "")
        else:
            # Для локального хранилища возвращаем пути
            bucket_map = {
                "upload": str(settings.UPLOAD_DIR),
                "processing": str(settings.PROCESSING_DIR),
                "processed": str(settings.PROCESSED_DIR),
                "json": str(settings.JSON_OUTPUT_DIR),
            }
            return bucket_map.get(bucket_type, "")

    async def get_audio_files(self, bucket_type: str = "upload") -> List[str]:
        """Получение списка аудиофайлов в bucket"""
        try:
            bucket = self._get_bucket_name(bucket_type)
            if not bucket:
                logger.warning("bucket.not.found", bucket_type=bucket_type)
                return []

            files = await self.storage.list_files(bucket)

            # Фильтруем по расширению
            audio_files = [
                f for f in files
                if Path(f).suffix.lower() in settings.SUPPORTED_AUDIO_FORMATS
            ]

            logger.debug(
                "audio.files.retrieved",
                bucket_type=bucket_type,
                count=len(audio_files)
            )
            return audio_files
        except Exception as e:
            logger.error("get.audio.files.error", error=str(e))
            return []

    async def validate_audio_file(
        self, 
        bucket_type: str,
        object_name: str
    ) -> bool:
        """Валидация аудиофайла в хранилище"""
        try:
            bucket = self._get_bucket_name(bucket_type)
            if not bucket:
                return False

            # Проверяем расширение
            if Path(object_name).suffix.lower() not in settings.SUPPORTED_AUDIO_FORMATS:
                logger.warning(
                    "file.format.not.supported",
                    object_name=object_name,
                    format=Path(object_name).suffix
                )
                return False

            # Проверяем существование файла
            exists = await self.storage.file_exists(bucket, object_name)
            if not exists:
                logger.warning("file.not.exists", object_name=object_name)
                return False

            # Для MinIO можно добавить проверку размера через stat_object
            # Для локального хранилища это не критично

            return True
        except Exception as e:
            logger.error(
                "validate.audio.file.error",
                object_name=object_name,
                error=str(e)
            )
            return False

    async def move_file(
        self,
        source_bucket: str,
        destination_bucket: str,
        object_name: str,
        temp_path: Optional[Path] = None
    ) -> Optional[str]:
        """
        Перемещение файла между buckets.
        
        Для MinIO: использует copy + delete
        Для локального хранилища: использует временный файл
        """
        try:
            source = self._get_bucket_name(source_bucket)
            dest = self._get_bucket_name(destination_bucket)

            if not source or not dest:
                logger.error(
                    "invalid.bucket.names",
                    source=source_bucket,
                    dest=destination_bucket
                )
                return None

            if settings.USE_MINIO:
                # Для MinIO копируем и удаляем
                # Note: MinIO Python SDK не имеет встроенного метода copy,
                # поэтому используем download -> upload -> delete
                
                # Временный файл
                import tempfile
                temp_file = tempfile.NamedTemporaryFile(delete=False)
                temp_path = temp_file.name
                temp_file.close()

                # Скачиваем
                success = await self.storage.download_file(
                    source, object_name, temp_path
                )
                if not success:
                    return None

                # Загружаем в новый bucket
                success = await self.storage.upload_file(
                    temp_path, dest, object_name
                )
                if not success:
                    return None

                # Удаляем исходный
                await self.storage.delete_file(source, object_name)

                # Удаляем временный файл
                import os
                os.unlink(temp_path)

            else:
                # Для локального хранилища просто копируем
                await self.storage.upload_file(
                    str(Path(source) / object_name),
                    dest,
                    object_name
                )
                # Удаляем исходный
                await self.storage.delete_file(source, object_name)

            logger.info(
                "file.moved",
                object_name=object_name,
                source_bucket=source_bucket,
                dest_bucket=destination_bucket
            )
            return object_name

        except Exception as e:
            logger.error(
                "move.file.error",
                object_name=object_name,
                error=str(e)
            )
            return None
    async def move_file(
        self,
        source_bucket: str,
        destination_bucket: str,
        object_name: str,
        temp_path: Optional[Path] = None,
    ) -> Optional[str]:
        """
        Переместить файл между bucket'ами.
        
        Работает как с полными именами bucket'ов ("audio-uploads"),
        так и с типами ("upload", "processing")
        
        Args:
            source_bucket: Исходный bucket (имя или тип)
            destination_bucket: Целевой bucket (имя или тип)
            object_name: Имя объекта в bucket'е
            temp_path: Путь для временного файла (опционально)
        
        Returns:
            object_name если успешно, None если ошибка
        """
        try:
            # ✅ Нормализуем bucket names
            # Если это тип (upload/processing/etc) - преобразуем в реальное имя
            # Если это уже реальное имя - используем как есть
            
            source = self._normalize_bucket_name(source_bucket)
            dest = self._normalize_bucket_name(destination_bucket)
            
            if not source or not dest:
                logger.error(
                    "invalid.bucket.names",
                    source=source_bucket,
                    dest=destination_bucket,
                )
                return None
            
            logger.debug(
                "move.file.starting",
                object_name=object_name,
                from_bucket=source,
                to_bucket=dest,
            )
            
            # ========== ЕСЛИ ОДИНАКОВЫЕ BUCKET'Ы ==========
            if source == dest:
                logger.warning(
                    "move.file.same.bucket",
                    object_name=object_name,
                    bucket=source,
                )
                return object_name
            
            # ========== ЕСЛИ MinIO ==========
            if settings.USE_MINIO:
                # ✅ В MinIO: copy + delete
                logger.debug(
                    "move.file.minio.copy",
                    object_name=object_name,
                    from_bucket=source,
                    to_bucket=dest,
                )
                
                # Копируем объект в новый bucket
                copy_success = await self.storage.copy_object(
                    source_bucket=source,
                    dest_bucket=dest,
                    object_name=object_name,
                )
                
                if not copy_success:
                    logger.error(
                        "move.file.copy.failed",
                        object_name=object_name,
                        from_bucket=source,
                        to_bucket=dest,
                    )
                    return None
                
                logger.debug(
                    "move.file.copied",
                    object_name=object_name,
                    from_bucket=source,
                    to_bucket=dest,
                )
                
                # Удаляем из исходного bucket
                delete_success = await self.storage.delete_file(
                    bucket=source,
                    object_name=object_name,
                )
                
                if not delete_success:
                    logger.error(
                        "move.file.delete.failed",
                        object_name=object_name,
                        from_bucket=source,
                    )
                    # ✅ Copy был успешен, это некритично
                    pass
                
                logger.info(
                    "file.moved",
                    object_name=object_name,
                    source_bucket=source_bucket,
                    dest_bucket=destination_bucket,
                )
                
                return object_name
            
            # ========== ЕСЛИ LOCAL STORAGE ==========
            else:
                # ✅ В Local: переместить через файловую систему
                from pathlib import Path
                import shutil
                
                logger.debug(
                    "move.file.local.move",
                    object_name=object_name,
                    from_path=source,
                    to_path=dest,
                )
                
                source_path = Path(source) / object_name
                dest_path = Path(dest) / object_name
                
                # Убедиться что целевая директория существует
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Переместить файл
                try:
                    shutil.move(str(source_path), str(dest_path))
                    
                    logger.info(
                        "file.moved",
                        object_name=object_name,
                        source_bucket=source_bucket,
                        dest_bucket=destination_bucket,
                    )
                    
                    return object_name
                
                except Exception as move_error:
                    logger.error(
                        "move.file.local.failed",
                        object_name=object_name,
                        from_path=source,
                        to_path=dest,
                        error=str(move_error),
                    )
                    return None
        
        except Exception as e:
            logger.error(
                "move.file.error",
                object_name=object_name,
                source_bucket=source_bucket,
                dest_bucket=destination_bucket,
                error=str(e),
            )
            return None

    def _normalize_bucket_name(self, bucket_input: str) -> Optional[str]:
        """
        Нормализовать имя bucket'а.
        
        Если это тип ("upload") - преобразовать в реальное имя ("audio-uploads")
        Если это уже имя - вернуть как есть
        
        Args:
            bucket_input: Имя или тип bucket'а
        
        Returns:
            Реальное имя bucket'а или None
        """
        if not bucket_input:
            return None
        
        # Если это стандартный тип - преобразуем
        bucket_types = {
            "upload": settings.MINIO_UPLOADS_BUCKET if settings.USE_MINIO else str(settings.UPLOAD_DIR),
            "processing": settings.MINIO_PROCESSING_BUCKET if settings.USE_MINIO else str(settings.PROCESSING_DIR),
            "processed": settings.MINIO_PROCESSED_BUCKET if settings.USE_MINIO else str(settings.PROCESSED_DIR),
            "json": settings.MINIO_JSON_OUTPUT_BUCKET if settings.USE_MINIO else str(settings.JSON_OUTPUT_DIR),
        }
        
        # Если это известный тип - вернуть реальное имя
        if bucket_input in bucket_types:
            return bucket_types[bucket_input]
        
        # Иначе вернуть как есть (это уже реальное имя)
        return bucket_input

    async def save_transcription_result(
        self,
        result: Dict[str, Any],
        object_name: str
    ) -> Optional[str]:
        """Сохранение результата транскрипции в JSON"""
        try:
            import tempfile
            import json as json_lib

            # Создаём временный JSON файл
            json_name = f"{Path(object_name).stem}.json"
            temp_file = tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.json',
                delete=False,
                encoding='utf-8'
            )

            json_lib.dump(result, temp_file, ensure_ascii=False, indent=2)
            temp_path = temp_file.name
            temp_file.close()

            # Загружаем в bucket JSON
            json_bucket = self._get_bucket_name("json")
            success = await self.storage.upload_file(temp_path, json_bucket, json_name)

            # Удаляем временный файл
            import os
            os.unlink(temp_path)

            if success:
                logger.info(
                    "transcription.result.saved",
                    object_name=object_name,
                    json_name=json_name
                )
                return json_name

            return None
        except Exception as e:
            logger.error(
                "save.transcription.result.failed",
                object_name=object_name,
                error=str(e)
            )
            return None

    async def cleanup_processing_bucket(self) -> None:
        """Очистка bucket с файлами в обработке"""
        try:
            bucket = self._get_bucket_name("processing")
            files = await self.storage.list_files(bucket)

            for file_name in files:
                await self.storage.delete_file(bucket, file_name)

            logger.info(
                "processing.bucket.cleaned",
                files_deleted=len(files)
            )
        except Exception as e:
            logger.error("cleanup.processing.bucket.error", error=str(e))

    async def get_processing_files(self) -> List[str]:
        """Получить список файлов в обработке (для восстановления при перезапуске)"""
        try:
            bucket = self._get_bucket_name("processing")
            files = await self.storage.list_files(bucket)

            # Фильтруем по расширению
            audio_files = [
                f for f in files
                if Path(f).suffix.lower() in settings.SUPPORTED_AUDIO_FORMATS
            ]

            logger.info(
                "processing.files.retrieved",
                count=len(audio_files)
            )
            return audio_files
        except Exception as e:
            logger.error("get.processing.files.error", error=str(e))
            return []

    async def download_file_for_processing(
        self,
        object_name: str,
        local_path: str
    ) -> bool:
        """
        Скачивание файла из upload bucket для локальной обработки.
        
        Используется если нужно обработать файл локально перед отправкой в API.
        """
        try:
            bucket = self._get_bucket_name("upload")
            success = await self.storage.download_file(bucket, object_name, local_path)

            if success:
                logger.info(
                    "file.downloaded.for.processing",
                    object_name=object_name,
                    local_path=local_path
                )
            return success
        except Exception as e:
            logger.error(
                "download.file.for.processing.error",
                object_name=object_name,
                error=str(e)
            )
            return False

    async def upload_processed_file_from_local(
        self,
        local_path: str,
        object_name: str,
        bucket_type: str = "processing"
    ) -> bool:
        """
        Загрузка обработанного файла из локальной системы в bucket.
        
        Используется если обработка происходит локально.
        """
        try:
            bucket = self._get_bucket_name(bucket_type)
            success = await self.storage.upload_file(local_path, bucket, object_name)

            if success:
                logger.info(
                    "file.uploaded.to.bucket",
                    object_name=object_name,
                    bucket_type=bucket_type
                )
            return success
        except Exception as e:
            logger.error(
                "upload.processed.file.error",
                object_name=object_name,
                error=str(e)
            )
            return False