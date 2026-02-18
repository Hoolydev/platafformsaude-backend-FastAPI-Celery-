"""
Configurações da Aplicação - Pydantic Settings
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Lê variáveis de ambiente do .env"""

    # Database
    DATABASE_URL: str

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""

    # Redis
    REDIS_URL: str = ""

    # Celery
    CELERY_BROKER_URL: str = ""

    # JWT
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"

    # Evolution API (WhatsApp)
    EVOLUTION_API_URL: str = ""
    EVOLUTION_API_KEY: str = ""

    # AI
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    ELEVENLABS_API_KEY: str = ""

    # MinIO / S3
    MINIO_ENDPOINT: str = ""
    MINIO_ACCESS_KEY: str = ""
    MINIO_SECRET_KEY: str = ""
    MINIO_BUCKET_NAME: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
