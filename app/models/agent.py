"""
Agent Models - Agentes de IA e suas ferramentas
"""

from sqlalchemy import Column, String, Text, Boolean, Integer, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class AgentToolType(str, enum.Enum):
    """Tipos de ferramentas disponíveis para agentes"""
    AGENDAR = "agendar"
    CANCELAR = "cancelar"
    BUSCAR_HORARIOS = "buscar_horarios"
    ESCALAR = "escalar"  # Escalar para humano
    FOLLOW_UP = "follow_up"
    CONSULTAR_PROCEDIMENTO = "consultar_procedimento"
    ENVIAR_DOCUMENTO = "enviar_documento"


class Agent(Base):
    """
    Modelo de Agente de IA
    
    Cada agente tem instruções específicas e pode usar diferentes ferramentas
    """
    __tablename__ = "agents"
    
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    
    nome = Column(String(255), nullable=False)
    instrucoes = Column(Text, nullable=False)  # System prompt
    
    # Configurações de LLM
    modelo_llm = Column(String(100), default="gpt-4", nullable=False)
    temperatura = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=2000)
    
    # Configurações de voz (ElevenLabs)
    voz_elevenlabs = Column(String(100), nullable=True)
    usar_voz = Column(Boolean, default=False)
    
    ativo = Column(Boolean, default=True, nullable=False)
    
    # Configurações adicionais
    configuracoes = Column(JSON, default=dict, nullable=False)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="agents")
    tools = relationship("AgentTool", back_populates="agent", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="agent")
    
    def __repr__(self):
        return f"<Agent {self.nome} - {self.modelo_llm}>"


class AgentTool(Base):
    """
    Modelo de Ferramenta do Agente
    
    Define quais ferramentas um agente pode usar e suas configurações
    """
    __tablename__ = "agent_tools"
    
    agent_id = Column(Integer, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    
    tipo = Column(SQLEnum(AgentToolType), nullable=False)
    ativo = Column(Boolean, default=True, nullable=False)
    
    # Configurações específicas da ferramenta
    configuracoes = Column(JSON, default=dict, nullable=False)
    
    # Relationships
    agent = relationship("Agent", back_populates="tools")
    
    def __repr__(self):
        return f"<AgentTool {self.tipo} for Agent {self.agent_id}>"
