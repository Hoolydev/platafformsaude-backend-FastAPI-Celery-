"""
Messages routes
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.message import Message, MessageOrigem, MessageTipo
from app.models.conversation import Conversation
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.message import MessageCreate, MessageResponse
from app.auth.dependencies import get_current_user, get_current_tenant

router = APIRouter(prefix="/conversations", tags=["messages"])


@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
async def list_messages(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
):
    # Verifica que a conversa pertence ao tenant
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.tenant_id == tenant.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversa não encontrada")

    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.criado_em)
    )
    return result.scalars().all()


@router.post("/{conversation_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    conversation_id: int,
    payload: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
):
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.tenant_id == tenant.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversa não encontrada")

    message = Message(
        conversation_id=conversation_id,
        tenant_id=tenant.id,
        origem=MessageOrigem.atendente,
        tipo=payload.tipo or MessageTipo.texto,
        conteudo=payload.conteudo,
        metadados=payload.metadados or {},
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return message
