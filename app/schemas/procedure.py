"""
Schemas: Procedure
"""

from typing import Optional, List, Any
from decimal import Decimal
from pydantic import BaseModel


class ProcedureCreate(BaseModel):
    tenant_id: int
    nome: str
    duracao_minutos: Optional[int] = None
    valor: Optional[Decimal] = None
    convenios_aceitos: Optional[List[Any]] = []
    descricao: Optional[str] = None


class ProcedureResponse(BaseModel):
    id: int
    tenant_id: int
    nome: str
    duracao_minutos: Optional[int] = None
    valor: Optional[Decimal] = None
    convenios_aceitos: Optional[List[Any]] = []
    descricao: Optional[str] = None

    model_config = {"from_attributes": True}
