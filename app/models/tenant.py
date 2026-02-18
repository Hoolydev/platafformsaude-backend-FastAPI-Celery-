"""
Model: Tenant
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.database import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(255), nullable=False)
    subdominio = Column(String(100), unique=True, nullable=False, index=True)
    ativo = Column(Boolean, default=True, nullable=False)
    configuracoes = Column(JSONB, default={})
    criado_em = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
