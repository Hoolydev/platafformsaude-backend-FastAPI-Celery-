"""
Procedures CRUD routes
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.procedure import Procedure
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.procedure import ProcedureCreate, ProcedureResponse
from app.auth.dependencies import get_current_user, get_current_tenant

router = APIRouter(prefix="/procedures", tags=["procedures"])


@router.get("/", response_model=List[ProcedureResponse])
async def list_procedures(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
):
    result = await db.execute(select(Procedure).where(Procedure.tenant_id == tenant.id))
    return result.scalars().all()


@router.get("/{procedure_id}", response_model=ProcedureResponse)
async def get_procedure(
    procedure_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
):
    result = await db.execute(
        select(Procedure).where(Procedure.id == procedure_id, Procedure.tenant_id == tenant.id)
    )
    proc = result.scalar_one_or_none()
    if not proc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Procedimento não encontrado")
    return proc


@router.post("/", response_model=ProcedureResponse, status_code=status.HTTP_201_CREATED)
async def create_procedure(
    payload: ProcedureCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
):
    data = payload.model_dump()
    data["tenant_id"] = tenant.id
    proc = Procedure(**data)
    db.add(proc)
    await db.commit()
    await db.refresh(proc)
    return proc


@router.put("/{procedure_id}", response_model=ProcedureResponse)
async def update_procedure(
    procedure_id: int,
    payload: ProcedureCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
):
    result = await db.execute(
        select(Procedure).where(Procedure.id == procedure_id, Procedure.tenant_id == tenant.id)
    )
    proc = result.scalar_one_or_none()
    if not proc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Procedimento não encontrado")

    for key, value in payload.model_dump().items():
        setattr(proc, key, value)

    await db.commit()
    await db.refresh(proc)
    return proc


@router.delete("/{procedure_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_procedure(
    procedure_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
):
    result = await db.execute(
        select(Procedure).where(Procedure.id == procedure_id, Procedure.tenant_id == tenant.id)
    )
    proc = result.scalar_one_or_none()
    if not proc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Procedimento não encontrado")
    await db.delete(proc)
    await db.commit()
