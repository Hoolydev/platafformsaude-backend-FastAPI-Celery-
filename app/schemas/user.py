"""
User Schemas
"""

from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from datetime import datetime
from app.models.user import UserRole


class UserBase(BaseModel):
    """Base schema para User"""
    nome: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    role: UserRole = Field(default=UserRole.ATENDENTE)


class UserCreate(UserBase):
    """Schema para criação de User"""
    senha: str = Field(..., min_length=8, description="Senha (mínimo 8 caracteres)")
    telefone: Optional[str] = Field(None, max_length=20)


class UserUpdate(BaseModel):
    """Schema para atualização de User"""
    nome: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    ativo: Optional[bool] = None
    telefone: Optional[str] = None
    avatar_url: Optional[str] = None


class UserResponse(UserBase):
    """Schema de resposta de User"""
    id: int
    tenant_id: int
    ativo: bool
    telefone: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class UserLogin(BaseModel):
    """Schema para login"""
    email: EmailStr = Field(..., description="Email do usuário")
    senha: str = Field(..., description="Senha")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "admin@clinica.com",
                "senha": "senha123"
            }
        }
    }


class ChangePassword(BaseModel):
    """Schema para mudança de senha"""
    senha_atual: str = Field(..., description="Senha atual")
    senha_nova: str = Field(..., min_length=8, description="Nova senha (mínimo 8 caracteres)")
