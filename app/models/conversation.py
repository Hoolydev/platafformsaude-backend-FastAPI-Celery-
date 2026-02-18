"""
Conversation Model - Conversas/Atendimentos
"""

from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class ConversationStatus(str, enum.Enum):
    """Status da conversa"""
    ATIVO = "ativo"  # Conversa ativa com agente IA
    ASSUMIDO = "assumido"  # Assumida por atendente humano
    CONCLUIDO = "concluido"  # Conversa finalizada


class ConversationChannel(str, enum.Enum):
    """Canal de comunicação"""
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"
    WEBCHAT = "webchat"
    SMS = "sms"


class Conversation(Base):
    """
    Modelo de Conversa/Atendimento
    
    Representa uma thread de conversa entre um contato e o sistema
    """
    __tablename__ = "conversations"
    
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    contact_id = Column(Integer, ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False, index=True)
    
    canal = Column(SQLEnum(ConversationChannel), default=ConversationChannel.WHATSAPP, nullable=False)
    status = Column(SQLEnum(ConversationStatus), default=ConversationStatus.ATIVO, nullable=False, index=True)
    
    # Controle de agente IA vs humano
    agente_ativo = Column(Boolean, default=True, nullable=False)
    atendente_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Agente IA responsável
    agent_id = Column(Integer, ForeignKey("agents.id", ondelete="SET NULL"), nullable=True)
    
    # Metadata da conversa
    assunto = Column(String(500), nullable=True)
    resumo = Column(String(2000), nullable=True)  # Gerado por IA
    
    # Relationships
    tenant = relationship("Tenant", back_populates="conversations")
    contact = relationship("Contact", back_populates="conversations")
    atendente = relationship("User", back_populates="conversations_atendidas", foreign_keys=[atendente_id])
    agent = relationship("Agent", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")
    lead_recoveries = relationship("LeadRecovery", back_populates="conversation", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Conversation {self.id} - {self.status} - Canal: {self.canal}>"
