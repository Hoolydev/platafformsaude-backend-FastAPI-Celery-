"""
WhatsApp instances routes
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.database import get_db
from app.models.whatsapp import WhatsappConnection, WhatsappProvider
from app.models.tenant import Tenant
from app.models.user import User
from app.auth.dependencies import get_current_user, get_current_tenant

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


class WhatsappCreate(BaseModel):
    numero: str
    provider: WhatsappProvider
    credenciais: Optional[Dict[str, Any]] = {}


class WhatsappResponse(BaseModel):
    id: int
    tenant_id: int
    numero: str
    provider: WhatsappProvider
    ativo: bool

    model_config = {"from_attributes": True}


@router.get("/instances", response_model=List[WhatsappResponse])
async def list_instances(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
):
    result = await db.execute(
        select(WhatsappConnection).where(WhatsappConnection.tenant_id == tenant.id)
    )
    return result.scalars().all()


@router.post("/instances", response_model=WhatsappResponse, status_code=status.HTTP_201_CREATED)
async def create_instance(
    payload: WhatsappCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
):
    conn = WhatsappConnection(tenant_id=tenant.id, **payload.model_dump())
    db.add(conn)
    await db.commit()
    await db.refresh(conn)
    return conn


@router.delete("/instances/{instance_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_instance(
    instance_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
):
    result = await db.execute(
        select(WhatsappConnection).where(
            WhatsappConnection.id == instance_id,
            WhatsappConnection.tenant_id == tenant.id,
        )
    )
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instância não encontrada")
    await db.delete(conn)
    await db.commit()
