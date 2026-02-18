"""
Contact Schemas
"""

from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime


class ContactBase(BaseModel):
    """Base schema para Contact"""
    telefone: str = Field(..., min_length=10, max_length=20, description="Telefone com DDD")
    nome: Optional[str] = Field(None, max_length=255)
    email: Optional[EmailStr] = None


class ContactCreate(ContactBase):
    """Schema para criação de Contact"""
    metadados: Dict[str, Any] = Field(default_factory=dict, description="Metadados adicionais (CPF, data nascimento, etc)")
    tags: List[str] = Field(default_factory=list, description="Tags para segmentação")


class ContactUpdate(BaseModel):
    """Schema para atualização de Contact"""
    nome: Optional[str] = Field(None, max_length=255)
    email: Optional[EmailStr] = None
    metadados: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None


class ContactResponse(ContactBase):
    """Schema de resposta de Contact"""
    id: int
    tenant_id: int
    metadados: Dict[str, Any]
    tags: List[str]
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
