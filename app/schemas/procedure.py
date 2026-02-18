"""
Procedure Schemas
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime


class ProcedureBase(BaseModel):
    """Base schema para Procedure"""
    nome: str = Field(..., min_length=1, max_length=255)
    descricao: Optional[str] = None
    duracao_minutos: int = Field(..., ge=5, le=480, description="Duração em minutos")


class ProcedureCreate(ProcedureBase):
    """Schema para criação de Procedure"""
    valor: Optional[float] = Field(None, ge=0, description="Valor do procedimento")
    convenios_aceitos: List[str] = Field(default_factory=list, description="Lista de convênios aceitos")
    categoria: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class ProcedureUpdate(BaseModel):
    """Schema para atualização de Procedure"""
    nome: Optional[str] = None
    descricao: Optional[str] = None
    duracao_minutos: Optional[int] = Field(None, ge=5, le=480)
    valor: Optional[float] = Field(None, ge=0)
    convenios_aceitos: Optional[List[str]] = None
    categoria: Optional[str] = None
    tags: Optional[List[str]] = None
    ativo: Optional[bool] = None


class ProcedureResponse(ProcedureBase):
    """Schema de resposta de Procedure"""
    id: int
    tenant_id: int
    valor: Optional[float] = None
    convenios_aceitos: List[str]
    categoria: Optional[str] = None
    tags: List[str]
    ativo: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
