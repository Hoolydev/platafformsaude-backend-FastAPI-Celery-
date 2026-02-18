"""
Model: Message
"""

import enum
from sqlalchemy import Column, Integer, String, ForeignKey, Enum, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.database import Base


class MessageOrigem(str, enum.Enum):
    cliente = "cliente"
    agente = "agente"
    atendente = "atendente"


class MessageTipo(str, enum.Enum):
    texto = "texto"
    audio = "audio"
    imagem = "imagem"
    documento = "documento"


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    origem = Column(Enum(MessageOrigem), nullable=False)
    tipo = Column(Enum(MessageTipo), default=MessageTipo.texto, nullable=False)
    conteudo = Column(Text, nullable=False)
    metadados = Column(JSONB, default={})
    criado_em = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
