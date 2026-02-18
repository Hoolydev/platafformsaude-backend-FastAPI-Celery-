"""
Webhooks routes — recebe eventos dos providers WhatsApp e publica no Redis
"""

from typing import Any, Dict
from fastapi import APIRouter, Request, BackgroundTasks
import json
import redis.asyncio as aioredis

from app.config import settings

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


async def _publish_to_redis(channel: str, payload: Dict[str, Any]) -> None:
    """Publica payload normalizado no Redis pub/sub."""
    try:
        r = aioredis.from_url(settings.REDIS_URL or "redis://localhost:6379")
        await r.publish(channel, json.dumps(payload))
        await r.aclose()
    except Exception:
        pass  # Não bloqueia o webhook se Redis estiver indisponível


def _normalize(provider: str, tenant_id: int, raw: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    return {
        "provider": provider,
        "tenant_id": tenant_id,
        "raw": raw,
        **kwargs,
    }


@router.post("/evolution/{tenant_id}/{instance_name}")
async def webhook_evolution(
    tenant_id: int,
    instance_name: str,
    request: Request,
    background_tasks: BackgroundTasks,
):
    raw = await request.json()
    payload = _normalize("evolution", tenant_id, raw, instance_name=instance_name)
    background_tasks.add_task(_publish_to_redis, f"whatsapp:{tenant_id}", payload)
    return {"status": "received"}


@router.post("/zapi/{tenant_id}/{connection_id}")
async def webhook_zapi(
    tenant_id: int,
    connection_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
):
    raw = await request.json()
    payload = _normalize("zapi", tenant_id, raw, connection_id=connection_id)
    background_tasks.add_task(_publish_to_redis, f"whatsapp:{tenant_id}", payload)
    return {"status": "received"}


@router.post("/uazapi/{tenant_id}/{connection_id}")
async def webhook_uazapi(
    tenant_id: int,
    connection_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
):
    raw = await request.json()
    payload = _normalize("uazapi", tenant_id, raw, connection_id=connection_id)
    background_tasks.add_task(_publish_to_redis, f"whatsapp:{tenant_id}", payload)
    return {"status": "received"}


@router.post("/oficial/{tenant_id}/{connection_id}")
async def webhook_oficial(
    tenant_id: int,
    connection_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
):
    raw = await request.json()
    payload = _normalize("oficial", tenant_id, raw, connection_id=connection_id)
    background_tasks.add_task(_publish_to_redis, f"whatsapp:{tenant_id}", payload)
    return {"status": "received"}
