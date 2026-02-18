"""
Auth Dependencies - FastAPI dependencies para autenticação
"""

from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from app.database import get_db
from app.models.user import User, UserRole
from app.auth.jwt import verify_token

# Security scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency para obter o usuário atual a partir do token JWT
    
    Raises:
        HTTPException: Se o token for inválido ou o usuário não existir
    
    Returns:
        Usuário autenticado
    """
    token = credentials.credentials
    
    # Verificar token
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verificar tipo de token
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tipo de token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Obter user_id do payload
    user_id: int = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Buscar usuário no banco
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency para obter usuário ativo
    
    Raises:
        HTTPException: Se o usuário estiver inativo
    
    Returns:
        Usuário ativo
    """
    if not current_user.ativo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário inativo"
        )
    
    return current_user


def require_role(*allowed_roles: UserRole):
    """
    Dependency factory para verificar roles
    
    Usage:
        @app.get("/admin")
        async def admin_endpoint(user: User = Depends(require_role(UserRole.ADMIN))):
            ...
    
    Args:
        allowed_roles: Roles permitidas
    
    Returns:
        Dependency function
    """
    async def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acesso negado. Roles permitidas: {[r.value for r in allowed_roles]}"
            )
        return current_user
    
    return role_checker


async def get_tenant_id_from_header(
    x_tenant_id: Optional[str] = Header(None)
) -> Optional[int]:
    """
    Obtém tenant_id do header X-Tenant-ID
    
    Returns:
        tenant_id se presente no header
    """
    if x_tenant_id:
        try:
            return int(x_tenant_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="X-Tenant-ID inválido"
            )
    return None
