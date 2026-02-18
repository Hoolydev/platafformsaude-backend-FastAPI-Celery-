"""
Users Endpoints - CRUD de usuários
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserUpdate, UserResponse, ChangePassword
from app.auth.dependencies import get_current_active_user, require_role
from app.auth.password import hash_password, verify_password
from app.middleware.tenant import get_tenant_id

router = APIRouter()


@router.get("/", response_model=List[UserResponse], summary="Listar usuários")
async def list_users(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Lista todos os usuários do tenant"""
    tenant_id = get_tenant_id(request) or current_user.tenant_id
    
    result = await db.execute(
        select(User)
        .where(User.tenant_id == tenant_id)
        .offset(skip)
        .limit(limit)
    )
    users = result.scalars().all()
    return users


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="Criar usuário")
async def create_user(
    request: Request,
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """Cria um novo usuário (apenas admins)"""
    tenant_id = get_tenant_id(request) or current_user.tenant_id
    
    # Verificar se email já existe no tenant
    result = await db.execute(
        select(User).where(
            User.tenant_id == tenant_id,
            User.email == user_data.email
        )
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email já cadastrado neste tenant"
        )
    
    # Criar usuário
    user = User(
        tenant_id=tenant_id,
        nome=user_data.nome,
        email=user_data.email,
        senha_hash=hash_password(user_data.senha),
        role=user_data.role,
        telefone=user_data.telefone
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return user


@router.get("/me", response_model=UserResponse, summary="Obter usuário atual")
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """Retorna informações do usuário autenticado"""
    return current_user


@router.get("/{user_id}", response_model=UserResponse, summary="Obter usuário por ID")
async def get_user(
    user_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Obtém um usuário específico"""
    tenant_id = get_tenant_id(request) or current_user.tenant_id
    
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.tenant_id == tenant_id
        )
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    return user


@router.patch("/{user_id}", response_model=UserResponse, summary="Atualizar usuário")
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """Atualiza um usuário (apenas admins)"""
    tenant_id = get_tenant_id(request) or current_user.tenant_id
    
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.tenant_id == tenant_id
        )
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    # Atualizar campos
    update_data = user_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    await db.commit()
    await db.refresh(user)
    
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Deletar usuário")
async def delete_user(
    user_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """Deleta um usuário (apenas admins)"""
    tenant_id = get_tenant_id(request) or current_user.tenant_id
    
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.tenant_id == tenant_id
        )
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    # Não permitir deletar a si mesmo
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível deletar seu próprio usuário"
        )
    
    await db.delete(user)
    await db.commit()
    
    return None


@router.post("/me/change-password", summary="Mudar senha")
async def change_password(
    password_data: ChangePassword,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Permite ao usuário mudar sua própria senha"""
    # Verificar senha atual
    if not verify_password(password_data.senha_atual, current_user.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Senha atual incorreta"
        )
    
    # Atualizar senha
    current_user.senha_hash = hash_password(password_data.senha_nova)
    await db.commit()
    
    return {"message": "Senha alterada com sucesso"}
