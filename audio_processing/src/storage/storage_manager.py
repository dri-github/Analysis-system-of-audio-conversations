import asyncio
import json
import io
from typing import Optional, List, Dict, Any, BinaryIO
from pathlib import Path
from datetime import datetime
from abc import ABC, abstractmethod

import structlog
from minio import Minio
from minio.error import S3Error
from config.settings import settings
from minio.commonconfig import CopySource
            
logger = structlog.get_logger()


class StorageBackend(ABC):
    """Абстрактный класс для работы с хранилищем"""

    @abstractmethod
    async def start(self) -> None:
        """Инициализация подключения"""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Закрытие подключения"""
        pass

    @abstractmethod
    async def upload_file(
        self, 
        file_path: str, 
        bucket: str, 
        object_name: str
    ) -> bool:
        """Загрузка файла в хранилище"""
        pass

    @abstractmethod
    async def download_file(
        self, 
        bucket: str, 
        object_name: str, 
        file_path: str
    ) -> bool:
        """Скачивание файла из хранилища"""
        pass

    @abstractmethod
    async def get_file_data(
        self, 
        bucket: str, 
        object_name: str
    ) -> Optional[bytes]:
        """Получение содержимого файла"""
        pass

    @abstractmethod
    async def list_files(
        self, 
        bucket: str, 
        prefix: str = ""
    ) -> List[str]:
        """Получение списка файлов в bucket"""
        pass

    @abstractmethod
    async def delete_file(
        self, 
        bucket: str, 
        object_name: str
    ) -> bool:
        """Удаление файла"""
        pass

    @abstractmethod
    async def file_exists(
        self, 
        bucket: str, 
        object_name: str
    ) -> bool:
        """Проверка наличия файла"""
        pass

    @abstractmethod
    async def create_bucket_if_not_exists(self, bucket: str) -> bool:
        """Создание bucket если его нет"""
        pass


class MinIOStorageBackend(StorageBackend):
    """Реализация хранилища на основе MinIO"""

    def __init__(self):
        self.client: Optional[Minio] = None
        self.endpoint = settings.MINIO_ENDPOINT
        self.access_key = settings.MINIO_ACCESS_KEY
        self.secret_key = settings.MINIO_SECRET_KEY
        self.secure = settings.MINIO_SECURE
        self.region = settings.MINIO_REGION

    async def start(self) -> None:
        """Инициализация MinIO клиента"""
        try:
            self.client = Minio(
                self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.secure,
                region=self.region,
            )
            logger.info("minio.connected", endpoint=self.endpoint)
        except Exception as e:
            logger.error("minio.connection.failed", error=str(e))
            raise
        
    async def stop(self) -> None:
        """Закрытие подключения"""
        self.client = None
        logger.info("minio.disconnected")

    async def create_bucket_if_not_exists(self, bucket: str) -> bool:
        """Создание bucket если его нет"""
        if not self.client:
            return False

        try:
            loop = asyncio.get_event_loop()
            
            # Проверяем существует ли bucket
            exists = await loop.run_in_executor(
                None,
                lambda: self.client.bucket_exists(bucket)
            )
            
            if not exists:
                # Создаём bucket
                await loop.run_in_executor(
                    None,
                    lambda: self.client.make_bucket(bucket, region=self.region)
                )
                logger.info("bucket.created", bucket=bucket)
            else:
                logger.debug("bucket.exists", bucket=bucket)
            
            return True
        except S3Error as e:
            logger.error("bucket.operation.failed", bucket=bucket, error=str(e))
            return False

    async def upload_file(
        self, 
        file_path: str, 
        bucket: str, 
        object_name: str
    ) -> bool:
        """Загрузка файла в MinIO"""
        if not self.client:
            return False

        try:
            loop = asyncio.get_event_loop()
            
            # Получаем размер файла
            file_size = Path(file_path).stat().st_size
            
            # Загружаем файл
            await loop.run_in_executor(
                None,
                lambda: self.client.fput_object(
                    bucket,
                    object_name,
                    file_path,
                    part_size=5_242_880  # 5 MB chunks
                )
            )
            
            logger.info(
                "file.uploaded",
                bucket=bucket,
                object_name=object_name,
                size_bytes=file_size
            )
            return True
        except S3Error as e:
            logger.error(
                "file.upload.failed",
                bucket=bucket,
                object_name=object_name,
                error=str(e)
            )
            return False

    async def download_file(
        self, 
        bucket: str, 
        object_name: str, 
        file_path: str
    ) -> bool:
        """Скачивание файла из MinIO"""
        if not self.client:
            return False

        try:
            loop = asyncio.get_event_loop()
            
            # Создаём директорию если её нет
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Скачиваем файл
            await loop.run_in_executor(
                None,
                lambda: self.client.fget_object(
                    bucket,
                    object_name,
                    file_path
                )
            )
            
            logger.info(
                "file.downloaded",
                bucket=bucket,
                object_name=object_name,
                file_path=file_path
            )
            return True
        except S3Error as e:
            logger.error(
                "file.download.failed",
                bucket=bucket,
                object_name=object_name,
                error=str(e)
            )
            return False

    async def get_file_data(
        self, 
        bucket: str, 
        object_name: str
    ) -> Optional[bytes]:
        """Получение содержимого файла"""
        if not self.client:
            return None

        try:
            loop = asyncio.get_event_loop()
            
            response = await loop.run_in_executor(
                None,
                lambda: self.client.get_object(bucket, object_name)
            )
            
            data = await loop.run_in_executor(
                None,
                lambda: response.read()
            )
            
            response.close()
            response.release_conn()
            
            logger.debug(
                "file.data.retrieved",
                bucket=bucket,
                object_name=object_name,
                size_bytes=len(data)
            )
            return data
        except S3Error as e:
            logger.error(
                "file.data.retrieval.failed",
                bucket=bucket,
                object_name=object_name,
                error=str(e)
            )
            return None

    async def list_files(
        self, 
        bucket: str, 
        prefix: str = ""
    ) -> List[str]:
        """Получение списка файлов в bucket"""
        if not self.client:
            return []

        try:
            loop = asyncio.get_event_loop()
            
            objects = await loop.run_in_executor(
                None,
                lambda: self.client.list_objects(bucket, prefix=prefix)
            )
            
            file_names = [obj.object_name for obj in objects]
            
            logger.debug(
                "files.listed",
                bucket=bucket,
                prefix=prefix,
                count=len(file_names)
            )
            return file_names
        except S3Error as e:
            logger.error(
                "files.list.failed",
                bucket=bucket,
                error=str(e)
            )
            return []

    async def delete_file(
        self, 
        bucket: str, 
        object_name: str
    ) -> bool:
        """Удаление файла"""
        if not self.client:
            return False

        try:
            loop = asyncio.get_event_loop()
            
            await loop.run_in_executor(
                None,
                lambda: self.client.remove_object(bucket, object_name)
            )
            
            logger.info(
                "file.deleted",
                bucket=bucket,
                object_name=object_name
            )
            return True
        except S3Error as e:
            logger.error(
                "file.delete.failed",
                bucket=bucket,
                object_name=object_name,
                error=str(e)
            )
            return False

    async def file_exists(
        self, 
        bucket: str, 
        object_name: str
    ) -> bool:
        """Проверка наличия файла"""
        if not self.client:
            return False

        try:
            loop = asyncio.get_event_loop()
            
            self.client.stat_object(bucket, object_name)
            return True
        except S3Error:
            return False


class LocalStorageBackend(StorageBackend):
    """Реализация хранилища на основе локальной файловой системы"""

    async def start(self) -> None:
        """Инициализация (ничего не требуется)"""
        logger.info("local.storage.started")

    async def stop(self) -> None:
        """Закрытие (ничего не требуется)"""
        logger.info("local.storage.stopped")

    async def create_bucket_if_not_exists(self, bucket: str) -> bool:
        """Создание директории если её нет"""
        try:
            Path(bucket).mkdir(parents=True, exist_ok=True)
            logger.debug("directory.created", path=bucket)
            return True
        except Exception as e:
            logger.error("directory.creation.failed", path=bucket, error=str(e))
            return False

    async def upload_file(
        self, 
        file_path: str, 
        bucket: str, 
        object_name: str
    ) -> bool:
        """Копирование файла в директорию"""
        try:
            loop = asyncio.get_event_loop()
            
            dest_path = Path(bucket) / object_name
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            def copy_file():
                with open(file_path, 'rb') as src:
                    with open(dest_path, 'wb') as dst:
                        dst.write(src.read())
            
            await loop.run_in_executor(None, copy_file)
            
            logger.info(
                "file.uploaded",
                bucket=bucket,
                object_name=object_name
            )
            return True
        except Exception as e:
            logger.error(
                "file.upload.failed",
                bucket=bucket,
                object_name=object_name,
                error=str(e)
            )
            return False

    async def download_file(
        self, 
        bucket: str, 
        object_name: str, 
        file_path: str
    ) -> bool:
        """Копирование файла из директории"""
        try:
            loop = asyncio.get_event_loop()
            
            src_path = Path(bucket) / object_name
            
            if not src_path.exists():
                logger.warning("file.not.found", path=src_path)
                return False
            
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            def copy_file():
                with open(src_path, 'rb') as src:
                    with open(file_path, 'wb') as dst:
                        dst.write(src.read())
            
            await loop.run_in_executor(None, copy_file)
            
            logger.info(
                "file.downloaded",
                bucket=bucket,
                object_name=object_name,
                file_path=file_path
            )
            return True
        except Exception as e:
            logger.error(
                "file.download.failed",
                bucket=bucket,
                object_name=object_name,
                error=str(e)
            )
            return False

    async def get_file_data(
        self, 
        bucket: str, 
        object_name: str
    ) -> Optional[bytes]:
        """Получение содержимого файла"""
        try:
            loop = asyncio.get_event_loop()
            
            file_path = Path(bucket) / object_name
            
            if not file_path.exists():
                logger.warning("file.not.found", path=file_path)
                return None
            
            def read_file():
                with open(file_path, 'rb') as f:
                    return f.read()
            
            data = await loop.run_in_executor(None, read_file)
            
            logger.debug(
                "file.data.retrieved",
                bucket=bucket,
                object_name=object_name,
                size_bytes=len(data)
            )
            return data
        except Exception as e:
            logger.error(
                "file.data.retrieval.failed",
                bucket=bucket,
                object_name=object_name,
                error=str(e)
            )
            return None

    async def list_files(
        self, 
        bucket: str, 
        prefix: str = ""
    ) -> List[str]:
        """Получение списка файлов в директории"""
        try:
            loop = asyncio.get_event_loop()
            
            def list_dir():
                bucket_path = Path(bucket)
                if not bucket_path.exists():
                    return []
                
                prefix_path = bucket_path / prefix
                if not prefix_path.exists():
                    return []
                
                return [
                    str(f.relative_to(bucket_path))
                    for f in prefix_path.rglob('*')
                    if f.is_file()
                ]
            
            files = await loop.run_in_executor(None, list_dir)
            
            logger.debug(
                "files.listed",
                bucket=bucket,
                prefix=prefix,
                count=len(files)
            )
            return files
        except Exception as e:
            logger.error(
                "files.list.failed",
                bucket=bucket,
                error=str(e)
            )
            return []

    async def delete_file(
        self, 
        bucket: str, 
        object_name: str
    ) -> bool:
        """Удаление файла"""
        try:
            loop = asyncio.get_event_loop()
            
            file_path = Path(bucket) / object_name
            
            if not file_path.exists():
                logger.warning("file.not.found", path=file_path)
                return False
            
            def delete_file_sync():
                file_path.unlink()
            
            await loop.run_in_executor(None, delete_file_sync)
            
            logger.info(
                "file.deleted",
                bucket=bucket,
                object_name=object_name
            )
            return True
        except Exception as e:
            logger.error(
                "file.delete.failed",
                bucket=bucket,
                object_name=object_name,
                error=str(e)
            )
            return False

    async def file_exists(
        self, 
        bucket: str, 
        object_name: str
    ) -> bool:
        """Проверка наличия файла"""
        file_path = Path(bucket) / object_name
        return file_path.exists()


class StorageManager:
    """Менеджер хранилища - абстракция для работы с MinIO или локальной FS"""

    def __init__(self):
        if settings.USE_MINIO:
            self.backend: StorageBackend = MinIOStorageBackend()
            logger.info("using.minio.storage")
        else:
            self.backend: StorageBackend = LocalStorageBackend()
            logger.info("using.local.storage")

    async def start(self) -> None:
        """Инициализация"""
        await self.backend.start()

    async def stop(self) -> None:
        """Остановка"""
        await self.backend.stop()

    async def upload_file(
        self, 
        file_path: str, 
        bucket: str, 
        object_name: str
    ) -> bool:
        """Загрузка файла"""
        return await self.backend.upload_file(file_path, bucket, object_name)

    async def download_file(
        self, 
        bucket: str, 
        object_name: str, 
        file_path: str
    ) -> bool:
        """Скачивание файла"""
        return await self.backend.download_file(bucket, object_name, file_path)

    async def get_file_data(
        self, 
        bucket: str, 
        object_name: str
    ) -> Optional[bytes]:
        """Получение содержимого файла"""
        return await self.backend.get_file_data(bucket, object_name)

    async def list_files(
        self, 
        bucket: str, 
        prefix: str = ""
    ) -> List[str]:
        """Получение списка файлов"""
        return await self.backend.list_files(bucket, prefix)

    async def delete_file(
        self, 
        bucket: str, 
        object_name: str
    ) -> bool:
        """Удаление файла"""
        return await self.backend.delete_file(bucket, object_name)

    async def file_exists(
        self, 
        bucket: str, 
        object_name: str
    ) -> bool:
        """Проверка наличия файла"""
        return await self.backend.file_exists(bucket, object_name)

    async def create_bucket_if_not_exists(self, bucket: str) -> bool:
        """Создание bucket"""
        return await self.backend.create_bucket_if_not_exists(bucket)
    
    async def _copy_via_download_upload(
        self,
        source_bucket: str,
        dest_bucket: str,
        object_name: str,
    ) -> bool:
        """
        Fallback: скачать и загрузить файл.
        Используется для LocalStorage.
        """
        try:
            import tempfile
            
            # Скачать в временный файл
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp_path = tmp.name
            
            success = await self.download_file(
                bucket=source_bucket,
                object_name=object_name,
                filepath=tmp_path,
            )
            
            if not success:
                return False
            
            # Загрузить из временного файла
            success = await self.upload_file(
                filepath=tmp_path,
                bucket=dest_bucket,
                object_name=object_name,
            )
            
            # Удалить временный файл
            import os
            try:
                os.unlink(tmp_path)
            except:
                pass
            
            return success
        
        except Exception as e:
            logger.error(
                "copy.via.download.upload.failed",
                error=str(e),
            )
            return False
    async def copy_object(
        self,
        source_bucket: str,
        dest_bucket: str,
        object_name: str,
    ) -> bool:
        """✅ БЕЗ ВРЕМЕННЫХ ФАЙЛОВ!"""
        try:
            # ✅ ШАГ 1: Получить байты в памяти
            file_data = await self.get_file_data(
                bucket=source_bucket,
                object_name=object_name,
            )
            
            if not file_data:
                return False
            
            # ✅ ШАГ 2: Загрузить напрямую
            success = await self._upload_bytes(
                file_data=file_data,
                bucket=dest_bucket,
                object_name=object_name,
            )
            
            return success
        
        except Exception as e:
            logger.error("object.copy.failed", error=str(e))
            return False


    async def _upload_bytes(
        self,
        file_data: bytes,
        bucket: str,
        object_name: str,
    ) -> bool:
        """✅ Загрузить байты БЕЗ ФАЙЛА!"""
        try:
            if isinstance(self.backend, MinIOStorageBackend):
                if not self.backend.client:
                    return False
                
                loop = asyncio.get_event_loop()
                
                # ✅ put_object принимает bytes напрямую!
                await loop.run_in_executor(
                    None,
                    lambda: self.backend.client.put_object(
                        bucket_name=bucket,
                        object_name=object_name,
                        data=io.BytesIO(file_data),
                        length=len(file_data),
                    ),
                )
                
                return True
            else:
                # LocalStorage
                loop = asyncio.get_event_loop()
                dest_path = Path(bucket) / object_name
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                
                def write_bytes():
                    with open(dest_path, 'wb') as f:
                        f.write(file_data)
                
                await loop.run_in_executor(None, write_bytes)
                return True
        
        except Exception as e:
            logger.error("bytes.upload.failed", error=str(e))
            return False
