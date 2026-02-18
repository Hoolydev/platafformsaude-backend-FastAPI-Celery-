"""
Models: Agent e AgentTool
"""

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from app.database import Base


class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    nome = Column(String(255), nullable=False)
    instrucoes = Column(Text)
    modelo_llm = Column(String(100), default="gpt-4o")
    voz_elevenlabs = Column(String(100))
    ativo = Column(Boolean, default=True, nullable=False)
    configuracoes = Column(JSONB, default={})


class AgentTool(Base):
    __tablename__ = "agent_tools"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False, index=True)
    tipo = Column(String(100), nullable=False)
    configuracoes = Column(JSONB, default={})
    ativo = Column(Boolean, default=True, nullable=False)
