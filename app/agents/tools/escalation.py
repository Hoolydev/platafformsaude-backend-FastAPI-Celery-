"""
Tool: Escalation — escalar conversa para atendente humano
"""

from typing import Optional
import json
import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.config import settings
from app.models.conversation import Conversation, ConversationStatus


async def escalar(
    db: AsyncSession,
    tenant_id: int,
    conversation_id: int,
    motivo: Optional[str] = None,
) -> dict:
    """
    Escala a conversa para atendente humano:
    1. Atualiza status para 'assumido' e desativa agente
    2. Publica alerta no Redis: channel saude:alerts:{tenant_id}
    """
    # Atualiza conversa no banco
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.tenant_id == tenant_id,
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        return {"erro": "Conversa não encontrada"}

    conv.status = ConversationStatus.assumido
    conv.agente_ativo = False
    await db.commit()

    # Publica no Redis
    alert_payload = {
        "tipo": "escalacao",
        "tenant_id": tenant_id,
        "conversation_id": conversation_id,
        "motivo": motivo or "Solicitado pelo agente",
    }

    try:
        r = aioredis.from_url(settings.REDIS_URL or "redis://localhost:6379")
        await r.publish(f"saude:alerts:{tenant_id}", json.dumps(alert_payload))
        await r.aclose()
    except Exception:
        pass  # Não bloqueia se Redis estiver indisponível

    return {"escalado": True, "conversation_id": conversation_id, "motivo": motivo}
