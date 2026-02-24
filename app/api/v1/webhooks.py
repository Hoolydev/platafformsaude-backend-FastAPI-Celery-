"""
Webhook endpoint para receber mensagens do WhatsApp
Compatível com Z-API e Evolution API
"""

from fastapi import APIRouter, Request, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.database import get_db
from app.models.contact import Contact
from app.models.conversation import Conversation, ConversationStatus
from app.models.message import Message, MessageOrigem, MessageTipo
from app.models.tenant import Tenant
from app.workers.tasks import processar_mensagem

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/zapi/{tenant_id}")
async def webhook_zapi(
    tenant_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Recebe mensagens da Z-API"""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="JSON inválido")

    # Z-API payload
    phone = body.get("phone", "")
    message = body.get("text", {}).get("message", "") if body.get("text") else ""
    is_from_me = body.get("fromMe", False)

    if is_from_me or not phone or not message:
        return {"ok": True, "info": "ignorado"}

    await processar_webhook(db, tenant_id, phone, message)
    return {"ok": True}


@router.post("/evolution/{tenant_id}")
async def webhook_evolution(
    tenant_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Recebe mensagens da Evolution API"""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="JSON inválido")

    # Evolution payload
    event = body.get("event", "")
    if event != "messages.upsert":
        return {"ok": True, "info": "evento ignorado"}

    data = body.get("data", {})
    key = data.get("key", {})
    is_from_me = key.get("fromMe", False)
    phone = key.get("remoteJid", "").replace("@s.whatsapp.net", "")
    message = data.get("message", {}).get("conversation", "")

    if is_from_me or not phone or not message:
        return {"ok": True, "info": "ignorado"}

    await processar_webhook(db, tenant_id, phone, message)
    return {"ok": True}


async def processar_webhook(
    db: AsyncSession,
    tenant_id: int,
    telefone: str,
    mensagem: str,
):
    # Verificar tenant
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant or not tenant.ativo:
        return

    # Buscar ou criar contato
    result = await db.execute(
        select(Contact).where(
            Contact.tenant_id == tenant_id,
            Contact.telefone == telefone,
        )
    )
    contato = result.scalar_one_or_none()
    if not contato:
        contato = Contact(
            tenant_id=tenant_id,
            telefone=telefone,
            nome=telefone,
        )
        db.add(contato)
        await db.flush()

    # Buscar ou criar conversa ativa
    result = await db.execute(
        select(Conversation).where(
            Conversation.tenant_id == tenant_id,
            Conversation.contact_id == contato.id,
            Conversation.status != ConversationStatus.concluido,
        ).order_by(Conversation.criado_em.desc()).limit(1)
    )
    conversa = result.scalar_one_or_none()
    if not conversa:
        conversa = Conversation(
            tenant_id=tenant_id,
            contact_id=contato.id,
            canal="whatsapp",
            status=ConversationStatus.ativo,
            agente_ativo=True,
        )
        db.add(conversa)
        await db.flush()

    # Salvar mensagem do cliente
    nova_msg = Message(
        conversation_id=conversa.id,
        tenant_id=tenant_id,
        origem=MessageOrigem.cliente,
        tipo=MessageTipo.texto,
        conteudo=mensagem,
    )
    db.add(nova_msg)
    await db.commit()

    # Disparar worker Celery
    processar_mensagem.delay(conversa.id, mensagem)
