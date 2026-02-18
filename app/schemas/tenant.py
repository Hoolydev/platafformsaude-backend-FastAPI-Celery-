"""
Tenant Schemas
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime


class TenantBase(BaseModel):
    """Base schema para Tenant"""
    nome: str = Field(..., min_length=1, max_length=255, description="Nome do tenant")
    subdominio: str = Field(..., min_length=1, max_length=100, description="Subdomínio único")
    plano: str = Field(default="trial", description="Plano contratado")
    configuracoes: Dict[str, Any] = Field(default_factory=dict, description="Configurações personalizadas")


class TenantCreate(TenantBase):
    """Schema para criação de Tenant"""
    limite_usuarios: Optional[int] = Field(default=5, description="Limite de usuários")
    limite_agentes: Optional[int] = Field(default=2, description="Limite de agentes IA")
    limite_conversas_mes: Optional[int] = Field(default=1000, description="Limite de conversas por mês")


class TenantUpdate(BaseModel):
    """Schema para atualização de Tenant"""
    nome: Optional[str] = Field(None, min_length=1, max_length=255)
    ativo: Optional[bool] = None
    plano: Optional[str] = None
    configuracoes: Optional[Dict[str, Any]] = None
    limite_usuarios: Optional[int] = None
    limite_agentes: Optional[int] = None
    limite_conversas_mes: Optional[int] = None


class TenantResponse(TenantBase):
    """Schema de resposta de Tenant"""
    id: int
    ativo: bool
    limite_usuarios: int
    limite_agentes: int
    limite_conversas_mes: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
