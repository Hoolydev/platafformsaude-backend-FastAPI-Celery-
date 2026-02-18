"""
LeadRecovery Model - Recuperação de leads inativos
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.database import Base


class LeadRecoveryTrigger(enum.Enum):
    """Tipo de trigger que iniciou a recuperação"""
    INATIVO = "inativo"  # Iniciou conversa mas não agendou
    FALTOU = "faltou"  # Tinha consulta e faltou
    CANCELOU = "cancelou"  # Cancelou sem reagendar
    ORCAMENTO = "orcamento"  # Recebeu orçamento mas não respondeu


class LeadRecoveryStatus(enum.Enum):
    """Status da recuperação"""
    PENDENTE = "pendente"
    EM_ANDAMENTO = "em_andamento"
    RECUPERADO = "recuperado"
    DESISTIU = "desistiu"


class LeadRecovery(Base):
    """
    Recuperação de Leads
    
    Gerencia tentativas de recuperação de leads inativos
    """
    __tablename__ = "lead_recoveries"
    
    # Relacionamentos
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=False, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=True)
    
    # Tipo de trigger
    trigger_tipo = Column(
        SQLEnum(LeadRecoveryTrigger),
        nullable=False,
        index=True
    )
    
    # Status
    status = Column(
        SQLEnum(LeadRecoveryStatus),
        nullable=False,
        default=LeadRecoveryStatus.PENDENTE,
        index=True
    )
    
    # Controle de tentativas
    tentativa_atual = Column(Integer, nullable=False, default=0)
    max_tentativas = Column(Integer, nullable=False, default=3)
    
    # Agendamento
    proxima_tentativa_em = Column(DateTime, nullable=True, index=True)
    
    # Relacionamentos ORM
    tenant = relationship("Tenant", back_populates="lead_recoveries")
    contact = relationship("Contact", back_populates="lead_recoveries")
    conversation = relationship("Conversation", back_populates="lead_recoveries")
    
    def __repr__(self):
        return f"<LeadRecovery {self.id}: {self.trigger_tipo.value} - {self.status.value}>"
