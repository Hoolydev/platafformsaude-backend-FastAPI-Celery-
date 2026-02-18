"""
Model: WhatsappConnection
"""

import enum
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import JSONB
from app.database import Base


class WhatsappProvider(str, enum.Enum):
    evolution = "evolution"
    zapi = "zapi"
    uazapi = "uazapi"
    oficial = "oficial"


class WhatsappConnection(Base):
    __tablename__ = "whatsapp_connections"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    numero = Column(String(30), nullable=False)
    provider = Column(Enum(WhatsappProvider), nullable=False)
    credenciais = Column(JSONB, default={})
    ativo = Column(Boolean, default=True, nullable=False)
