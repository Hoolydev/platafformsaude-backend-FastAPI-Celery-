"""
Connection Models - Integrações externas
"""

from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class WhatsappProvider(str, enum.Enum):
    """Provedores de WhatsApp"""
    ZAPI = "zapi"
    UAZAPI = "uazapi"
    OFICIAL = "oficial"  # WhatsApp Business API oficial


class CalendarProvider(str, enum.Enum):
    """Provedores de Agenda"""
    GOOGLE = "google"
    FEEGOW = "feegow"
    DOCTORALIA = "doctoralia"


class WhatsappConnection(Base):
    """
    Modelo de Conexão WhatsApp
    
    Armazena credenciais e configurações de integração com WhatsApp
    """
    __tablename__ = "whatsapp_connections"
    
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    
    numero = Column(String(20), nullable=False)
    provider = Column(SQLEnum(WhatsappProvider), nullable=False)
    
    # Credenciais (criptografadas)
    credenciais = Column(JSON, nullable=False)  # instance_id, token, etc
    
    # Webhook
    webhook_url = Column(String(500), nullable=True)
    
    ativo = Column(Boolean, default=True, nullable=False)
    
    # Status da conexão
    conectado = Column(Boolean, default=False, nullable=False)
    # Configurações específicas por provider
    configuracoes = Column(JSON, nullable=True)  # Configurações adicionais
    
    # Configurações de voz
    modo_voz = Column(String(50), nullable=True, default="desabilitado")  # desabilitado, apenas_audio, retell
    elevenlabs_voice_id = Column(String(100), nullable=True)  # ID da voz no ElevenLabs
    retell_agent_id = Column(String(100), nullable=True)  # ID do agente no Retell AI
    
    # Relacionamentos
    tenant = relationship("Tenant", back_populates="whatsapp_connections")
    
    def __repr__(self):
        return f"<WhatsappConnection {self.numero} - {self.provider}>"


class CalendarConnection(Base):
    """
    Modelo de Conexão com Agenda
    
    Armazena credenciais e configurações de integração com sistemas de agenda
    """
    __tablename__ = "calendar_connections"
    
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    
    provider = Column(SQLEnum(CalendarProvider), nullable=False)
    
    # Credenciais (criptografadas)
    credenciais = Column(JSON, nullable=False)  # API keys, OAuth tokens, etc
    
    # ID da agenda no sistema externo
    id_agenda = Column(String(255), nullable=True)
    
    ativo = Column(Boolean, default=True, nullable=False)
    
    # Sincronização
    ultima_sincronizacao = Column(DateTime(timezone=True), nullable=True)
    sincronizacao_automatica = Column(Boolean, default=True)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="calendar_connections")
    
    def __repr__(self):
        return f"<CalendarConnection {self.provider} - Agenda: {self.id_agenda}>"
