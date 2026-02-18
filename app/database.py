"""
Database configuration - SQLAlchemy 2.0 com AsyncPG
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, declared_attr
from sqlalchemy import Column, Integer, DateTime, func
from typing import AsyncGenerator
import os

# Database URL
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://saude_user:SaudeSecurePass2024!@postgres:5432/saude_platform"
)

# Criar engine assíncrono
engine = create_async_engine(
    DATABASE_URL,
    echo=True if os.getenv("APP_DEBUG") == "true" else False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Base class para todos os modelos"""
    
    @declared_attr
    def __tablename__(cls) -> str:
        """Gera nome da tabela automaticamente a partir do nome da classe"""
        return cls.__name__.lower()
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency para obter sessão do banco de dados
    
    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Inicializa o banco de dados (cria todas as tabelas)"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Fecha conexões do banco de dados"""
    await engine.dispose()
