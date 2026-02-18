from pydantic_settings import BaseSettings
from pydantic import validator


class Settings(BaseSettings):
    DATABASE_URL: str = ""
    REDIS_URL: str = ""
    JWT_SECRET: str = "changeme"
    JWT_ALGORITHM: str = "HS256"
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    CELERY_BROKER_URL: str = ""
    CELERY_RESULT_BACKEND: str = ""
    EVOLUTION_API_URL: str = ""
    EVOLUTION_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    ELEVENLABS_API_KEY: str = ""
    MINIO_ENDPOINT: str = ""
    MINIO_ACCESS_KEY: str = ""
    MINIO_SECRET_KEY: str = ""
    MINIO_BUCKET_NAME: str = "saude-platform"
    ZAPI_BASE_URL: str = ""
    UAZAPI_BASE_URL: str = ""

    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()
