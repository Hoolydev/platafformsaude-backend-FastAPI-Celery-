"""
Conversation Schemas
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from app.models.conversation import ConversationStatus, ConversationChannel


class ConversationBase(BaseModel):
    """Base schema para Conversation"""
    canal: ConversationChannel = Field(default=ConversationChannel.WHATSAPP)
    assunto: Optional[str] = Field(None, max_length=500)


class ConversationCreate(ConversationBase):
    """Schema para criação de Conversation"""
    contact_id: int = Field(..., description="ID do contato")
    agent_id: Optional[int] = Field(None, description="ID do agente IA responsável")


class ConversationUpdate(BaseModel):
    """Schema para atualização de Conversation"""
    status: Optional[ConversationStatus] = None
    agente_ativo: Optional[bool] = None
    atendente_id: Optional[int] = None
    agent_id: Optional[int] = None
    assunto: Optional[str] = None
    resumo: Optional[str] = None


class ConversationResponse(ConversationBase):
    """Schema de resposta de Conversation"""
    id: int
    tenant_id: int
    contact_id: int
    status: ConversationStatus
    agente_ativo: bool
    atendente_id: Optional[int] = None
    agent_id: Optional[int] = None
    resumo: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
