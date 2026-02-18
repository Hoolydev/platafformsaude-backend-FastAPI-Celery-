"""
Agent Schemas
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime
from app.models.agent import AgentToolType


class AgentBase(BaseModel):
    """Base schema para Agent"""
    nome: str = Field(..., min_length=1, max_length=255)
    instrucoes: str = Field(..., min_length=10, description="Instruções/prompt do agente")
    modelo_llm: str = Field(default="gpt-4", description="Modelo LLM a usar")


class AgentCreate(AgentBase):
    """Schema para criação de Agent"""
    temperatura: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2000, ge=100, le=4000)
    voz_elevenlabs: Optional[str] = None
    usar_voz: bool = Field(default=False)
    configuracoes: Dict[str, Any] = Field(default_factory=dict)


class AgentUpdate(BaseModel):
    """Schema para atualização de Agent"""
    nome: Optional[str] = None
    instrucoes: Optional[str] = None
    modelo_llm: Optional[str] = None
    temperatura: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=100, le=4000)
    voz_elevenlabs: Optional[str] = None
    usar_voz: Optional[bool] = None
    ativo: Optional[bool] = None
    configuracoes: Optional[Dict[str, Any]] = None


class AgentToolCreate(BaseModel):
    """Schema para criação de AgentTool"""
    tipo: AgentToolType
    ativo: bool = Field(default=True)
    configuracoes: Dict[str, Any] = Field(default_factory=dict)


class AgentToolResponse(BaseModel):
    """Schema de resposta de AgentTool"""
    id: int
    agent_id: int
    tipo: AgentToolType
    ativo: bool
    configuracoes: Dict[str, Any]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class AgentResponse(AgentBase):
    """Schema de resposta de Agent"""
    id: int
    tenant_id: int
    temperatura: float
    max_tokens: int
    voz_elevenlabs: Optional[str] = None
    usar_voz: bool
    ativo: bool
    configuracoes: Dict[str, Any]
    tools: List[AgentToolResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
