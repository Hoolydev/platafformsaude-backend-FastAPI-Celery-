"""
Schemas: Message
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel
from app.models.message import MessageOrigem, MessageTipo


class MessageCreate(BaseModel):
    conversation_id: int
    tenant_id: int
    origem: MessageOrigem
    tipo: Optional[MessageTipo] = MessageTipo.texto
    conteudo: str
    metadados: Optional[Dict[str, Any]] = {}


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    tenant_id: int
    origem: MessageOrigem
    tipo: MessageTipo
    conteudo: str
    metadados: Optional[Dict[str, Any]] = {}
    criado_em: datetime

    model_config = {"from_attributes": True}
