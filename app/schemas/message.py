"""
Message Schemas
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime
from app.models.message import MessageOrigin, MessageType


class MessageBase(BaseModel):
    """Base schema para Message"""
    conteudo: str = Field(..., min_length=1, description="Conteúdo da mensagem")
    tipo: MessageType = Field(default=MessageType.TEXTO)


class MessageCreate(MessageBase):
    """Schema para criação de Message"""
    conversation_id: int = Field(..., description="ID da conversa")
    origem: MessageOrigin = Field(..., description="Origem da mensagem")
    metadados: Dict[str, Any] = Field(default_factory=dict, description="Metadados (URL mídia, etc)")
    external_id: Optional[str] = Field(None, description="ID externo (WhatsApp, etc)")


class MessageResponse(MessageBase):
    """Schema de resposta de Message"""
    id: int
    conversation_id: int
    tenant_id: int
    origem: MessageOrigin
    metadados: Dict[str, Any]
    external_id: Optional[str] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
