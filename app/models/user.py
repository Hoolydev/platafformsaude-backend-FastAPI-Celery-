"""
Model: User
"""

import enum
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Enum
from app.database import Base


class UserRole(str, enum.Enum):
    admin = "admin"
    atendente = "atendente"
    visualizador = "visualizador"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    nome = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    senha_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.atendente, nullable=False)
    ativo = Column(Boolean, default=True, nullable=False)
