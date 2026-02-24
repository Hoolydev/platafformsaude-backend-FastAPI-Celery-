"""
Worker: Message Processor — task principal de processamento de mensagens
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.config import settings

# Engine dedicado para workers (não compartilha com FastAPI)
_engine = None
_SessionLocal = None

def _get_session():
    global _engine, _SessionLocal
    if _engine is None:
        _engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
        _SessionLocal = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)
    return _SessionLocal


def get_celery():
    from app.workers.celery_app import celery_app
    return celery_app


def _task(*args, **kwargs):
    return get_celery().task(*args, **kwargs)


async def _process(tenant_id: int, message_data: Dict[str, Any]) -> None:
    from app.models.contact import Contact
    from app.models.conversation import Conversation, ConversationStatus
    from app.models.message import Message, MessageOrigem, MessageTipo
    from app.models.whatsapp import WhatsappConnection
    from app.models.agent import Agent
    from app.models.lead_recovery import LeadRecovery, LeadRecoveryStatus, LeadTriggerTipo
    from app.agents import memory as mem
    from app.agents.engine import run_agent
    from app.integrations.whatsapp.factory import WhatsAppFactory
    import redis.asyncio as aioredis

    telefone = message_data.get("from", "")
    conteudo = message_data.get("content", "")
    canal = message_data.get("provider", "evolution")

    async with _get_session()() as db:
        # 1. Buscar ou criar Contact
        result = await db.execute(
            select(Contact).where(Contact.tenant_id == tenant_id, Contact.telefone == telefone)
        )
        contact = result.scalar_one_or_none()
        if not contact:
            contact = Contact(tenant_id=tenant_id, telefone=telefone)
            db.add(contact)
            await db.flush()

        # 2. Buscar ou criar Conversation ativa
        result = await db.execute(
            select(Conversation).where(
                Conversation.tenant_id == tenant_id,
                Conversation.contact_id == contact.id,
                Conversation.status != ConversationStatus.concluido,
            ).order_by(Conversation.criado_em.desc())
        )
        conv = result.scalars().first()
        if not conv:
            conv = Conversation(
                tenant_id=tenant_id,
                contact_id=contact.id,
                canal=canal,
                status=ConversationStatus.ativo,
                agente_ativo=True,
            )
            db.add(conv)
            await db.flush()

        # 3. Salvar mensagem do cliente
        msg = Message(
            conversation_id=conv.id,
            tenant_id=tenant_id,
            origem=MessageOrigem.cliente,
            tipo=MessageTipo.texto,
            conteudo=conteudo,
            metadados=message_data,
        )
        db.add(msg)
        await db.commit()

        # 4. Verificar label agente-off nos metadados da conversa
        # (convenção: metadados da conversa podem ter {"labels": ["agente-off"]})
        # Conversations não tem metadados no model atual — verificamos via agente_ativo

        # 5. Verificar se agente está ativo
        if not conv.agente_ativo:
            # 7. Publicar alerta para atendente
            try:
                r = aioredis.from_url(settings.REDIS_URL or "redis://localhost:6379")
                await r.publish(
                    f"saude:alerts:{tenant_id}",
                    json.dumps({
                        "tipo": "nova_mensagem_humano",
                        "tenant_id": tenant_id,
                        "conversation_id": conv.id,
                        "contact_id": contact.id,
                        "mensagem": conteudo,
                    }),
                )
                await r.aclose()
            except Exception:
                pass
            return

        # 6. Agente ativo — buscar configuração do agente do tenant
        result = await db.execute(
            select(Agent).where(Agent.tenant_id == tenant_id, Agent.ativo == True)  # noqa: E712
        )
        agent = result.scalars().first()
        if not agent:
            return

        agent_config = {
            "modelo_llm": agent.modelo_llm or "gpt-4o",
            "instrucoes": agent.instrucoes or "",
            "voz_elevenlabs": agent.voz_elevenlabs,
            **(agent.configuracoes or {}),
        }

        # Chamar engine
        response = await run_agent(
            db=db,
            tenant_id=tenant_id,
            conversation_id=conv.id,
            contact_id=contact.id,
            message=conteudo,
            agent_config=agent_config,
        )

        # Enviar respostas com delays via WhatsApp
        result = await db.execute(
            select(WhatsappConnection).where(
                WhatsappConnection.tenant_id == tenant_id,
                WhatsappConnection.ativo == True,  # noqa: E712
            )
        )
        wa_conn = result.scalars().first()

        if wa_conn:
            provider = WhatsAppFactory.get_provider(
                wa_conn.provider.value, wa_conn.credenciais or {}
            )
            for part in response.get("mensagens", []):
                delay_s = part.get("delay_ms", 1000) / 1000
                await asyncio.sleep(delay_s)
                await provider.send_typing(to=telefone)
                await asyncio.sleep(min(delay_s * 0.5, 3))
                await provider.send_text(to=telefone, text=part["conteudo"])

        # Escalar se necessário
        if response.get("deve_escalar"):
            from app.agents.tools.escalation import escalar
            await escalar(db, tenant_id, conv.id, "Solicitado pelo agente")

        # 8. Verificar recuperação de lead (conversa sem agendamento há > 4h)
        from app.models.appointment import Appointment
        result = await db.execute(
            select(Appointment).where(
                Appointment.tenant_id == tenant_id,
                Appointment.contact_id == contact.id,
            ).order_by(Appointment.criado_em.desc())
        )
        last_appt = result.scalars().first()
        agora = datetime.now(timezone.utc)

        if not last_appt:
            conv_age = agora - conv.criado_em.replace(tzinfo=timezone.utc)
            if conv_age > timedelta(hours=4):
                # Verificar se já existe LeadRecovery
                result = await db.execute(
                    select(LeadRecovery).where(
                        LeadRecovery.tenant_id == tenant_id,
                        LeadRecovery.contact_id == contact.id,
                        LeadRecovery.status.in_([
                            LeadRecoveryStatus.pendente,
                            LeadRecoveryStatus.em_andamento,
                        ]),
                    )
                )
                existing = result.scalar_one_or_none()
                if not existing:
                    lr = LeadRecovery(
                        tenant_id=tenant_id,
                        contact_id=contact.id,
                        conversation_id=conv.id,
                        trigger_tipo=LeadTriggerTipo.inativo,
                        status=LeadRecoveryStatus.pendente,
                        proxima_tentativa_em=agora + timedelta(hours=1),
                    )
                    db.add(lr)
                    await db.commit()


# Celery task wrapper (sync → async)
def process_incoming_message(tenant_id: int, message_data: Dict[str, Any]) -> None:
    asyncio.run(_process(tenant_id, message_data))


# Registrar como task Celery de forma lazy
try:
    from app.workers.celery_app import celery_app
    process_incoming_message = celery_app.task(
        name="app.workers.message_processor.process_incoming_message",
        bind=False,
        max_retries=3,
        default_retry_delay=30,
    )(process_incoming_message)
except Exception:
    pass
