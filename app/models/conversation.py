"""
Model: Conversation
"""

import enum
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Enum, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class ConversationStatus(str, enum.Enum):
    ativo = "ativo"
    assumido = "assumido"
    concluido = "concluido"


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=False, index=True)
    canal = Column(String(50), nullable=False)
    status = Column(Enum(ConversationStatus), default=ConversationStatus.ativo, nullable=False)
    agente_ativo = Column(Boolean, default=True, nullable=False)
    atendente_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    contact = relationship("Contact", lazy="noload")

