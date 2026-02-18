"""
Worker: Lead Recovery — recuperação de leads inativos
"""

import asyncio
from datetime import datetime, timezone, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.config import settings

_engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
_SessionLocal = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


async def _verificar() -> None:
    from app.models.lead_recovery import LeadRecovery, LeadRecoveryStatus
    from app.models.contact import Contact
    from app.models.whatsapp import WhatsappConnection
    from app.integrations.whatsapp.factory import WhatsAppFactory
    from app.agents.tools.escalation import escalar
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage, SystemMessage

    agora = datetime.now(timezone.utc)

    async with _SessionLocal() as db:
        result = await db.execute(
            select(LeadRecovery).where(
                LeadRecovery.proxima_tentativa_em <= agora,
                LeadRecovery.status.in_([
                    LeadRecoveryStatus.pendente,
                    LeadRecoveryStatus.em_andamento,
                ]),
            )
        )
        leads = result.scalars().all()

        for lead in leads:
            # Buscar contato
            result = await db.execute(select(Contact).where(Contact.id == lead.contact_id))
            contact = result.scalar_one_or_none()
            if not contact:
                continue

            # Buscar conexão WhatsApp
            result = await db.execute(
                select(WhatsappConnection).where(
                    WhatsappConnection.tenant_id == lead.tenant_id,
                    WhatsappConnection.ativo == True,  # noqa: E712
                )
            )
            wa_conn = result.scalars().first()
            if not wa_conn:
                continue

            # Gerar mensagem via LLM com contexto do histórico
            try:
                from app.agents.memory import get_history
                historico = []
                if lead.conversation_id:
                    historico = await get_history(db, lead.conversation_id, limit=10)

                historico_texto = "\n".join(
                    f"{'Cliente' if h.origem.value == 'cliente' else 'Agente'}: {h.conteudo}"
                    for h in historico
                ) or "Sem histórico anterior."

                llm = ChatOpenAI(
                    model="gpt-4o-mini",
                    api_key=settings.OPENAI_API_KEY,
                    temperature=0.8,
                )
                mensagem_llm = await llm.ainvoke([
                    SystemMessage(content=(
                        "Você é um assistente de saúde. Gere uma mensagem curta e amigável "
                        "de follow-up para reconquistar um paciente que não agendou consulta. "
                        "Máximo 2 frases. Não mencione que é um bot."
                    )),
                    HumanMessage(content=(
                        f"Histórico da conversa:\n{historico_texto}\n\n"
                        f"Nome do paciente: {contact.nome or 'cliente'}\n"
                        f"Tentativa: {lead.tentativa_atual + 1} de {lead.max_tentativas}"
                    )),
                ])
                mensagem = mensagem_llm.content

                # Enviar via WhatsApp
                provider = WhatsAppFactory.get_provider(
                    wa_conn.provider.value, wa_conn.credenciais or {}
                )
                await provider.send_text(to=contact.telefone, text=mensagem)

                # Atualizar lead
                lead.tentativa_atual += 1
                lead.status = LeadRecoveryStatus.em_andamento

                if lead.tentativa_atual >= lead.max_tentativas:
                    lead.status = LeadRecoveryStatus.desistiu
                    # Escalar para humano
                    if lead.conversation_id:
                        await escalar(
                            db, lead.tenant_id, lead.conversation_id,
                            f"Lead não recuperado após {lead.max_tentativas} tentativas"
                        )
                else:
                    # Próxima tentativa em 24h
                    lead.proxima_tentativa_em = agora + timedelta(hours=24)

            except Exception:
                # Não bloqueia os outros leads
                pass

        await db.commit()


def verificar_recuperacao() -> None:
    asyncio.run(_verificar())


try:
    from app.workers.celery_app import celery_app
    verificar_recuperacao = celery_app.task(
        name="app.workers.lead_recovery.verificar_recuperacao"
    )(verificar_recuperacao)
except Exception:
    pass
