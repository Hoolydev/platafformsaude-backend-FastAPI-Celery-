"""
Message Model - Mensagens
"""

from sqlalchemy import Column, String, Text, Integer, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class MessageOrigin(str, enum.Enum):
    """Origem da mensagem"""
    CLIENTE = "cliente"
    AGENTE = "agente"  # IA
    ATENDENTE = "atendente"  # Humano


class MessageType(str, enum.Enum):
    """Tipo de mensagem"""
    TEXTO = "texto"
    AUDIO = "audio"
    IMAGEM = "imagem"
    DOCUMENTO = "documento"
    VIDEO = "video"
    LOCALIZACAO = "localizacao"
    CONTATO = "contato"


class Message(Base):
    """
    Modelo de Mensagem
    
    Armazena todas as mensagens trocadas em uma conversa
    """
    __tablename__ = "messages"
    
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    
    origem = Column(SQLEnum(MessageOrigin), nullable=False)
    tipo = Column(SQLEnum(MessageType), default=MessageType.TEXTO, nullable=False)
    
    # Conteúdo
    conteudo = Column(Text, nullable=False)
    
    # Metadados (URL de mídia, transcrição de áudio, etc)
    metadados = Column(JSON, default=dict, nullable=False)
    
    # ID externo (do WhatsApp, por exemplo)
    external_id = Column(String(255), nullable=True, index=True)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    
    def __repr__(self):
        return f"<Message {self.id} - {self.origem} - {self.tipo}>"
    
    @property
    def is_from_client(self) -> bool:
        return self.origem == MessageOrigin.CLIENTE
    
    @property
    def is_from_ai(self) -> bool:
        return self.origem == MessageOrigin.AGENTE
