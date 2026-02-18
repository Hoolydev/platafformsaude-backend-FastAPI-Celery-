"""
Storage Service - MinIO Client
"""

from minio import Minio
from app.config import settings


_minio_client = None


def get_minio_client() -> Minio:
    """Retorna cliente MinIO singleton"""
    global _minio_client
    
    if _minio_client is None:
        _minio_client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE
        )
    
    return _minio_client
