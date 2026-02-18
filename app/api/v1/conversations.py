"""
Conversations Endpoints - CRUD de conversas
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List
from app.database import get_db
from app.models.user import User
from app.models.conversation import Conversation
from app.schemas.conversation import ConversationCreate, ConversationUpdate, ConversationResponse
from app.auth.dependencies import get_current_active_user
from app.middleware.tenant import get_tenant_id

router = APIRouter()


@router.get("/", response_model=List[ConversationResponse], summary="Listar conversas")
async def list_conversations(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Lista todas as conversas do tenant"""
    tenant_id = get_tenant_id(request) or current_user.tenant_id
    
    result = await db.execute(
        select(Conversation)
        .where(Conversation.tenant_id == tenant_id)
        .offset(skip)
        .limit(limit)
        .order_by(Conversation.created_at.desc())
    )
    conversations = result.scalars().all()
    return conversations


@router.post("/", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED, summary="Criar conversa")
async def create_conversation(
    request: Request,
    conversation_data: ConversationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Cria uma nova conversa"""
    tenant_id = get_tenant_id(request) or current_user.tenant_id
    
    # Criar conversa
    conversation = Conversation(
        tenant_id=tenant_id,
        contact_id=conversation_data.contact_id,
        canal=conversation_data.canal,
        assunto=conversation_data.assunto,
        agent_id=conversation_data.agent_id
    )
    
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    
    return conversation


@router.get("/{conversation_id}", response_model=ConversationResponse, summary="Obter conversa")
async def get_conversation(
    conversation_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Obtém uma conversa específica"""
    tenant_id = get_tenant_id(request) or current_user.tenant_id
    
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.tenant_id == tenant_id
        )
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversa não encontrada"
        )
    
    return conversation


@router.patch("/{conversation_id}", response_model=ConversationResponse, summary="Atualizar conversa")
async def update_conversation(
    conversation_id: int,
    conversation_data: ConversationUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Atualiza uma conversa"""
    tenant_id = get_tenant_id(request) or current_user.tenant_id
    
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.tenant_id == tenant_id
        )
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversa não encontrada"
        )
    
    # Atualizar campos
    update_data = conversation_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(conversation, field, value)
    
    await db.commit()
    await db.refresh(conversation)
    
    return conversation


@router.post("/{conversation_id}/assumir", response_model=ConversationResponse, summary="Assumir conversa")
async def assumir_conversa(
    conversation_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Atendente assume a conversa (desativa agente IA)"""
    tenant_id = get_tenant_id(request) or current_user.tenant_id
    
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.tenant_id == tenant_id
        )
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversa não encontrada"
        )
    
    # Assumir conversa
    conversation.agente_ativo = False
    conversation.atendente_id = current_user.id
    conversation.status = "assumido"
    
    await db.commit()
    await db.refresh(conversation)
    
    return conversation


@router.post("/{conversation_id}/finalizar", response_model=ConversationResponse, summary="Finalizar conversa")
async def finalizar_conversa(
    conversation_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Finaliza uma conversa"""
    tenant_id = get_tenant_id(request) or current_user.tenant_id
    
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.tenant_id == tenant_id
        )
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversa não encontrada"
        )
    
    # Finalizar conversa
    conversation.status = "concluido"
    conversation.agente_ativo = False
    
    await db.commit()
    await db.refresh(conversation)
    
    return conversation
