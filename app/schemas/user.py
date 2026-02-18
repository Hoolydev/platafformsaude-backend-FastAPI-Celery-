"""
Schemas: User
"""

from typing import Optional
from pydantic import BaseModel, EmailStr
from app.models.user import UserRole


class UserCreate(BaseModel):
    nome: str
    email: EmailStr
    senha: str
    role: Optional[UserRole] = UserRole.atendente
    tenant_id: int


class UserResponse(BaseModel):
    id: int
    tenant_id: int
    nome: str
    email: str
    role: UserRole
    ativo: bool

    model_config = {"from_attributes": True}


class UserLogin(BaseModel):
    email: EmailStr
    senha: str
