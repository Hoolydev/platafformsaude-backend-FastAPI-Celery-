"""
Model: LeadRecovery
"""

import enum
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func
from app.database import Base


class LeadTriggerTipo(str, enum.Enum):
    inativo = "inativo"
    faltou = "faltou"
    cancelou = "cancelou"


class LeadRecoveryStatus(str, enum.Enum):
    pendente = "pendente"
    em_andamento = "em_andamento"
    recuperado = "recuperado"
    desistiu = "desistiu"


class LeadRecovery(Base):
    __tablename__ = "lead_recoveries"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=False, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=True)
    trigger_tipo = Column(Enum(LeadTriggerTipo), nullable=False)
    status = Column(Enum(LeadRecoveryStatus), default=LeadRecoveryStatus.pendente, nullable=False)
    tentativa_atual = Column(Integer, default=0, nullable=False)
    max_tentativas = Column(Integer, default=3, nullable=False)
    proxima_tentativa_em = Column(DateTime(timezone=True), nullable=False, index=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
