"""
Agent Memory — persistência de mensagens e dados do contato no PostgreSQL
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.message import Message, MessageOrigem, MessageTipo
from app.models.contact import Contact


async def save_message(
    db: AsyncSession,
    conversation_id: int,
    tenant_id: int,
    origem: MessageOrigem,
    conteudo: str,
    tipo: MessageTipo = MessageTipo.texto,
    metadados: Optional[Dict[str, Any]] = None,
) -> Message:
    """Salva uma mensagem no PostgreSQL."""
    msg = Message(
        conversation_id=conversation_id,
        tenant_id=tenant_id,
        origem=origem,
        tipo=tipo,
        conteudo=conteudo,
        metadados=metadados or {},
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg


async def get_history(
    db: AsyncSession,
    conversation_id: int,
    limit: int = 20,
) -> List[Message]:
    """Busca as últimas N mensagens da conversa, em ordem cronológica."""
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.criado_em.desc())
        .limit(limit)
    )
    messages = result.scalars().all()
    return list(reversed(messages))


async def get_contact_info(db: AsyncSession, contact_id: int) -> Optional[Dict[str, Any]]:
    """Busca informações do contato (nome, email, metadados)."""
    result = await db.execute(select(Contact).where(Contact.id == contact_id))
    contact = result.scalar_one_or_none()
    if not contact:
        return None
    return {
        "id": contact.id,
        "nome": contact.nome,
        "email": contact.email,
        "telefone": contact.telefone,
        "metadados": contact.metadados or {},
    }


async def update_contact_info(
    db: AsyncSession,
    contact_id: int,
    updates: Dict[str, Any],
) -> None:
    """Atualiza metadados do contato."""
    await db.execute(
        update(Contact).where(Contact.id == contact_id).values(**updates)
    )
    await db.commit()
