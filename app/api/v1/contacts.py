"""
Contacts Endpoints - CRUD de contatos
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.database import get_db
from app.models.user import User
from app.models.contact import Contact
from app.schemas.contact import ContactCreate, ContactUpdate, ContactResponse
from app.auth.dependencies import get_current_active_user
from app.middleware.tenant import get_tenant_id

router = APIRouter()


@router.get("/", response_model=List[ContactResponse], summary="Listar contatos")
async def list_contacts(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Lista todos os contatos do tenant"""
    tenant_id = get_tenant_id(request) or current_user.tenant_id
    
    result = await db.execute(
        select(Contact)
        .where(Contact.tenant_id == tenant_id)
        .offset(skip)
        .limit(limit)
    )
    contacts = result.scalars().all()
    return contacts


@router.post("/", response_model=ContactResponse, status_code=status.HTTP_201_CREATED, summary="Criar contato")
async def create_contact(
    request: Request,
    contact_data: ContactCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Cria um novo contato"""
    tenant_id = get_tenant_id(request) or current_user.tenant_id
    
    # Verificar se telefone já existe no tenant
    result = await db.execute(
        select(Contact).where(
            Contact.tenant_id == tenant_id,
            Contact.telefone == contact_data.telefone
        )
    )
    existing_contact = result.scalar_one_or_none()
    
    if existing_contact:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Telefone já cadastrado neste tenant"
        )
    
    # Criar contato
    contact = Contact(
        tenant_id=tenant_id,
        telefone=contact_data.telefone,
        nome=contact_data.nome,
        email=contact_data.email,
        metadados=contact_data.metadados,
        tags=contact_data.tags
    )
    
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    
    return contact


@router.get("/{contact_id}", response_model=ContactResponse, summary="Obter contato")
async def get_contact(
    contact_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Obtém um contato específico"""
    tenant_id = get_tenant_id(request) or current_user.tenant_id
    
    result = await db.execute(
        select(Contact).where(
            Contact.id == contact_id,
            Contact.tenant_id == tenant_id
        )
    )
    contact = result.scalar_one_or_none()
    
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contato não encontrado"
        )
    
    return contact


@router.patch("/{contact_id}", response_model=ContactResponse, summary="Atualizar contato")
async def update_contact(
    contact_id: int,
    contact_data: ContactUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Atualiza um contato"""
    tenant_id = get_tenant_id(request) or current_user.tenant_id
    
    result = await db.execute(
        select(Contact).where(
            Contact.id == contact_id,
            Contact.tenant_id == tenant_id
        )
    )
    contact = result.scalar_one_or_none()
    
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contato não encontrado"
        )
    
    # Atualizar campos
    update_data = contact_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(contact, field, value)
    
    await db.commit()
    await db.refresh(contact)
    
    return contact


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Deletar contato")
async def delete_contact(
    contact_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Deleta um contato"""
    tenant_id = get_tenant_id(request) or current_user.tenant_id
    
    result = await db.execute(
        select(Contact).where(
            Contact.id == contact_id,
            Contact.tenant_id == tenant_id
        )
    )
    contact = result.scalar_one_or_none()
    
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contato não encontrado"
        )
    
    await db.delete(contact)
    await db.commit()
    
    return None
