"""
Tasks genéricas — follow-up e outras tasks avulsas
"""

import asyncio
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.config import settings

_engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
_SessionLocal = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


async def _send_followup(
    tenant_id: int,
    contact_id: int,
    mensagem: str,
    conversation_id: Optional[int] = None,
) -> None:
    from app.models.contact import Contact
    from app.models.whatsapp import WhatsappConnection
    from app.integrations.whatsapp.factory import WhatsAppFactory

    async with _SessionLocal() as db:
        result = await db.execute(select(Contact).where(Contact.id == contact_id))
        contact = result.scalar_one_or_none()
        if not contact:
            return

        result = await db.execute(
            select(WhatsappConnection).where(
                WhatsappConnection.tenant_id == tenant_id,
                WhatsappConnection.ativo == True,  # noqa: E712
            )
        )
        wa_conn = result.scalars().first()
        if not wa_conn:
            return

        provider = WhatsAppFactory.get_provider(
            wa_conn.provider.value, wa_conn.credenciais or {}
        )
        await provider.send_text(to=contact.telefone, text=mensagem)


def send_followup_message(
    tenant_id: int,
    contact_id: int,
    mensagem: str,
    conversation_id: Optional[int] = None,
) -> None:
    asyncio.run(_send_followup(tenant_id, contact_id, mensagem, conversation_id))


try:
    from app.workers.celery_app import celery_app
    send_followup_message = celery_app.task(
        name="app.workers.tasks.send_followup_message"
    )(send_followup_message)
except Exception:
    pass
