"""
Schemas: Conversation
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from app.models.conversation import ConversationStatus


class ContactBrief(BaseModel):
    nome: Optional[str] = None
    telefone: Optional[str] = None

    model_config = {"from_attributes": True}


class ConversationResponse(BaseModel):
    id: int
    tenant_id: int
    contact_id: int
    canal: str
    status: ConversationStatus
    agente_ativo: bool
    atendente_id: Optional[int] = None
    criado_em: datetime
    contact: Optional[ContactBrief] = None

    model_config = {"from_attributes": True}


class ConversationUpdate(BaseModel):
    status: Optional[ConversationStatus] = None
    agente_ativo: Optional[bool] = None
    atendente_id: Optional[int] = None

