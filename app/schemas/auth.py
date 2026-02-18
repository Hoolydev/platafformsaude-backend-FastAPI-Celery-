"""
Auth Schemas - Pydantic models para autenticação
"""

from pydantic import BaseModel, Field


class Token(BaseModel):
    """Schema de resposta de autenticação"""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Tipo do token")
    expires_in: int = Field(..., description="Tempo de expiração em segundos")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 1800
            }
        }
    }


class TokenRefresh(BaseModel):
    """Schema para refresh token"""
    refresh_token: str = Field(..., description="Refresh token para obter novo access token")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }
    }


class TokenResponse(BaseModel):
    """Schema de resposta após refresh"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
