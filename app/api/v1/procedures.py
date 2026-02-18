"""
Procedures Endpoints - CRUD de procedimentos
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.database import get_db
from app.models.user import User, UserRole
from app.models.procedure import Procedure
from app.schemas.procedure import ProcedureCreate, ProcedureUpdate, ProcedureResponse
from app.auth.dependencies import get_current_active_user, require_role
from app.middleware.tenant import get_tenant_id

router = APIRouter()


@router.get("/", response_model=List[ProcedureResponse], summary="Listar procedimentos")
async def list_procedures(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    ativo: bool = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Lista todos os procedimentos do tenant"""
    tenant_id = get_tenant_id(request) or current_user.tenant_id
    
    query = select(Procedure).where(Procedure.tenant_id == tenant_id)
    
    if ativo is not None:
        query = query.where(Procedure.ativo == ativo)
    
    result = await db.execute(
        query.offset(skip).limit(limit)
    )
    procedures = result.scalars().all()
    return procedures


@router.post("/", response_model=ProcedureResponse, status_code=status.HTTP_201_CREATED, summary="Criar procedimento")
async def create_procedure(
    request: Request,
    procedure_data: ProcedureCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.ATENDENTE))
):
    """Cria um novo procedimento"""
    tenant_id = get_tenant_id(request) or current_user.tenant_id
    
    # Criar procedimento
    procedure = Procedure(
        tenant_id=tenant_id,
        nome=procedure_data.nome,
        descricao=procedure_data.descricao,
        duracao_minutos=procedure_data.duracao_minutos,
        valor=procedure_data.valor,
        convenios_aceitos=procedure_data.convenios_aceitos,
        categoria=procedure_data.categoria,
        tags=procedure_data.tags
    )
    
    db.add(procedure)
    await db.commit()
    await db.refresh(procedure)
    
    return procedure


@router.get("/{procedure_id}", response_model=ProcedureResponse, summary="Obter procedimento")
async def get_procedure(
    procedure_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Obtém um procedimento específico"""
    tenant_id = get_tenant_id(request) or current_user.tenant_id
    
    result = await db.execute(
        select(Procedure).where(
            Procedure.id == procedure_id,
            Procedure.tenant_id == tenant_id
        )
    )
    procedure = result.scalar_one_or_none()
    
    if not procedure:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Procedimento não encontrado"
        )
    
    return procedure


@router.patch("/{procedure_id}", response_model=ProcedureResponse, summary="Atualizar procedimento")
async def update_procedure(
    procedure_id: int,
    procedure_data: ProcedureUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.ATENDENTE))
):
    """Atualiza um procedimento"""
    tenant_id = get_tenant_id(request) or current_user.tenant_id
    
    result = await db.execute(
        select(Procedure).where(
            Procedure.id == procedure_id,
            Procedure.tenant_id == tenant_id
        )
    )
    procedure = result.scalar_one_or_none()
    
    if not procedure:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Procedimento não encontrado"
        )
    
    # Atualizar campos
    update_data = procedure_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(procedure, field, value)
    
    await db.commit()
    await db.refresh(procedure)
    
    return procedure


@router.delete("/{procedure_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Deletar procedimento")
async def delete_procedure(
    procedure_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """Deleta um procedimento (apenas admins)"""
    tenant_id = get_tenant_id(request) or current_user.tenant_id
    
    result = await db.execute(
        select(Procedure).where(
            Procedure.id == procedure_id,
            Procedure.tenant_id == tenant_id
        )
    )
    procedure = result.scalar_one_or_none()
    
    if not procedure:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Procedimento não encontrado"
        )
    
    await db.delete(procedure)
    await db.commit()
    
    return None
