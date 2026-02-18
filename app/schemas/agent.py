"""
Schemas: Agent
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel


class AgentCreate(BaseModel):
    tenant_id: int
    nome: str
    instrucoes: Optional[str] = None
    modelo_llm: Optional[str] = "gpt-4o"
    voz_elevenlabs: Optional[str] = None
    configuracoes: Optional[Dict[str, Any]] = {}


class AgentResponse(BaseModel):
    id: int
    tenant_id: int
    nome: str
    instrucoes: Optional[str] = None
    modelo_llm: str
    voz_elevenlabs: Optional[str] = None
    ativo: bool
    configuracoes: Optional[Dict[str, Any]] = {}

    model_config = {"from_attributes": True}
