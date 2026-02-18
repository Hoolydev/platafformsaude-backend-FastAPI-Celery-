"""
Auth Endpoints - Login, Refresh, Logout
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserLogin
from app.schemas.auth import Token, TokenRefresh, TokenResponse
from app.auth.jwt import create_access_token, create_refresh_token, verify_token
from app.auth.password import verify_password
from datetime import timedelta
import os

router = APIRouter()

ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))


@router.post("/login", response_model=Token, summary="Login de usuário")
async def login(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """
    Autentica um usuário e retorna tokens JWT
    
    - **email**: Email do usuário
    - **senha**: Senha do usuário
    
    Returns:
        Token com access_token e refresh_token
    """
    # Buscar usuário por email
    result = await db.execute(
        select(User).where(User.email == credentials.email)
    )
    user = result.scalar_one_or_none()
    
    # Verificar se usuário existe
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verificar senha
    if not verify_password(credentials.senha, user.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verificar se usuário está ativo
    if not user.ativo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário inativo"
        )
    
    # Criar tokens
    token_data = {
        "user_id": user.id,
        "tenant_id": user.tenant_id,
        "email": user.email,
        "role": user.role.value
    }
    
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token({"user_id": user.id})
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/refresh", response_model=TokenResponse, summary="Renovar access token")
async def refresh_token(
    token_data: TokenRefresh,
    db: AsyncSession = Depends(get_db)
):
    """
    Renova o access token usando um refresh token válido
    
    - **refresh_token**: Refresh token JWT
    
    Returns:
        Novo access token
    """
    # Verificar refresh token
    payload = verify_token(token_data.refresh_token)
    
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Obter user_id
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Buscar usuário
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user or not user.ativo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado ou inativo"
        )
    
    # Criar novo access token
    token_data = {
        "user_id": user.id,
        "tenant_id": user.tenant_id,
        "email": user.email,
        "role": user.role.value
    }
    
    access_token = create_access_token(token_data)
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/logout", summary="Logout (placeholder)")
async def logout():
    """
    Logout do usuário
    
    Nota: Com JWT stateless, o logout é feito no client removendo o token.
    Este endpoint existe para compatibilidade e pode ser usado para blacklist de tokens no futuro.
    """
    return {"message": "Logout realizado com sucesso"}
