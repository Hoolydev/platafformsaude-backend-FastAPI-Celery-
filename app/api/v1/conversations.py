"""
Conversations routes
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.conversation import Conversation, ConversationStatus
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.conversation import ConversationResponse, ConversationUpdate
from app.auth.dependencies import get_current_user, get_current_tenant

router = APIRouter(prefix="/conversations", tags=["conversations"])


async def _get_conversation_or_404(
    conversation_id: int, tenant_id: int, db: AsyncSession
) -> Conversation:
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.tenant_id == tenant_id,
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversa não encontrada")
    return conv


@router.get("/", response_model=List[ConversationResponse])
async def list_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
):
    result = await db.execute(
        select(Conversation).where(Conversation.tenant_id == tenant.id)
    )
    return result.scalars().all()


@router.patch("/{conversation_id}/assumir", response_model=ConversationResponse)
async def assumir_conversa(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
):
    conv = await _get_conversation_or_404(conversation_id, tenant.id, db)
    conv.status = ConversationStatus.assumido
    conv.agente_ativo = False
    conv.atendente_id = current_user.id
    await db.commit()
    await db.refresh(conv)
    return conv


@router.patch("/{conversation_id}/concluir", response_model=ConversationResponse)
async def concluir_conversa(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
):
    conv = await _get_conversation_or_404(conversation_id, tenant.id, db)
    conv.status = ConversationStatus.concluido
    conv.agente_ativo = False
    await db.commit()
    await db.refresh(conv)
    return conv


@router.patch("/{conversation_id}/reativar-agente", response_model=ConversationResponse)
async def reativar_agente(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
):
    conv = await _get_conversation_or_404(conversation_id, tenant.id, db)
    conv.status = ConversationStatus.ativo
    conv.agente_ativo = True
    conv.atendente_id = None
    await db.commit()
    await db.refresh(conv)
    return conv
