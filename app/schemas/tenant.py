"""
Schemas: Tenant
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel


class TenantCreate(BaseModel):
    nome: str
    subdominio: str
    configuracoes: Optional[Dict[str, Any]] = {}


class TenantResponse(BaseModel):
    id: int
    nome: str
    subdominio: str
    ativo: bool
    configuracoes: Optional[Dict[str, Any]] = {}
    criado_em: datetime

    model_config = {"from_attributes": True}
