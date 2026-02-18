"""
Contacts CRUD routes (scoped to tenant)
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.database import get_db
from app.models.contact import Contact
from app.models.tenant import Tenant
from app.models.user import User
from app.auth.dependencies import get_current_user, get_current_tenant

router = APIRouter(prefix="/contacts", tags=["contacts"])


class ContactCreate(BaseModel):
    telefone: str
    nome: Optional[str] = None
    email: Optional[str] = None
    metadados: Optional[Dict[str, Any]] = {}


class ContactResponse(BaseModel):
    id: int
    tenant_id: int
    telefone: str
    nome: Optional[str] = None
    email: Optional[str] = None
    metadados: Optional[Dict[str, Any]] = {}

    model_config = {"from_attributes": True}


@router.get("/", response_model=List[ContactResponse])
async def list_contacts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
):
    result = await db.execute(select(Contact).where(Contact.tenant_id == tenant.id))
    return result.scalars().all()


@router.get("/{contact_id}", response_model=ContactResponse)
async def get_contact(
    contact_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
):
    result = await db.execute(
        select(Contact).where(Contact.id == contact_id, Contact.tenant_id == tenant.id)
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contato não encontrado")
    return contact


@router.post("/", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
async def create_contact(
    payload: ContactCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
):
    contact = Contact(tenant_id=tenant.id, **payload.model_dump())
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    return contact


@router.put("/{contact_id}", response_model=ContactResponse)
async def update_contact(
    contact_id: int,
    payload: ContactCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
):
    result = await db.execute(
        select(Contact).where(Contact.id == contact_id, Contact.tenant_id == tenant.id)
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contato não encontrado")

    for key, value in payload.model_dump().items():
        setattr(contact, key, value)

    await db.commit()
    await db.refresh(contact)
    return contact


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contact(
    contact_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
):
    result = await db.execute(
        select(Contact).where(Contact.id == contact_id, Contact.tenant_id == tenant.id)
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contato não encontrado")
    await db.delete(contact)
    await db.commit()
