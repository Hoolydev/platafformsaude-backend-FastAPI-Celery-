"""
Schemas: Flow
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class FlowNodeBase(BaseModel):
    id: Optional[int] = None
    tipo: str
    nome: Optional[str] = None
    posicao: Optional[Dict[str, Any]] = {"x": 0, "y": 0}
    configuracoes: Optional[Dict[str, Any]] = {}


class FlowEdgeBase(BaseModel):
    id: Optional[int] = None
    source_node_id: int
    target_node_id: int
    condicao: Optional[str] = None
    configuracoes: Optional[Dict[str, Any]] = {}


class FlowCreate(BaseModel):
    tenant_id: int
    nome: str
    descricao: Optional[str] = None
    ativo: Optional[bool] = True
    configuracoes: Optional[Dict[str, Any]] = {}
    nodes: Optional[List[FlowNodeBase]] = []
    edges: Optional[List[FlowEdgeBase]] = []


class FlowResponse(BaseModel):
    id: int
    tenant_id: int
    nome: str
    descricao: Optional[str] = None
    ativo: bool
    configuracoes: Optional[Dict[str, Any]] = {}

    model_config = {"from_attributes": True}


class FlowDetailResponse(FlowResponse):
    nodes: List[FlowNodeBase]
    edges: List[FlowEdgeBase]
