"""
Workers: Reminders — lembretes de consulta 24h e 2h
"""

import asyncio
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.config import settings

_engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
_SessionLocal = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


async def _enviar_lembrete(tipo: str) -> None:
    from app.models.appointment import Appointment, AppointmentStatus
    from app.models.reminder_log import ReminderLog
    from app.models.contact import Contact
    from app.models.whatsapp import WhatsappConnection
    from app.integrations.whatsapp.factory import WhatsAppFactory

    agora = datetime.now(timezone.utc)

    if tipo == "24h":
        inicio = agora + timedelta(hours=23)
        fim = agora + timedelta(hours=25)
        label = "24h"
        template = "Olá {nome}! Lembrando que você tem uma consulta amanhã às {hora}. Confirme sua presença respondendo SIM."
    elif tipo == "2h":
        inicio = agora + timedelta(hours=1, minutes=50)
        fim = agora + timedelta(hours=2, minutes=10)
        label = "2h"
        template = "Olá {nome}! Sua consulta é em aproximadamente 2 horas ({hora}). Estamos te esperando!"
    else:
        return

    async with _SessionLocal() as db:
        # Busca appointments no intervalo sem ReminderLog do tipo
        result = await db.execute(
            select(Appointment).where(
                and_(
                    Appointment.data_hora >= inicio,
                    Appointment.data_hora <= fim,
                    Appointment.status.in_([AppointmentStatus.agendado, AppointmentStatus.confirmado]),
                )
            )
        )
        appointments = result.scalars().all()

        for appt in appointments:
            # Verificar se já enviou este tipo de lembrete
            result = await db.execute(
                select(ReminderLog).where(
                    ReminderLog.appointment_id == appt.id,
                    ReminderLog.tipo_lembrete == label,
                )
            )
            if result.scalar_one_or_none():
                continue  # Já enviado

            # Buscar contato
            result = await db.execute(select(Contact).where(Contact.id == appt.contact_id))
            contact = result.scalar_one_or_none()
            if not contact:
                continue

            # Buscar conexão WhatsApp do tenant
            result = await db.execute(
                select(WhatsappConnection).where(
                    WhatsappConnection.tenant_id == appt.tenant_id,
                    WhatsappConnection.ativo == True,  # noqa: E712
                )
            )
            wa_conn = result.scalars().first()

            erro = None
            try:
                if wa_conn:
                    provider = WhatsAppFactory.get_provider(
                        wa_conn.provider.value, wa_conn.credenciais or {}
                    )
                    hora_local = appt.data_hora.strftime("%H:%M")
                    mensagem = template.format(
                        nome=contact.nome or "cliente",
                        hora=hora_local,
                    )
                    await provider.send_text(to=contact.telefone, text=mensagem)
                    status = "enviado"
                else:
                    status = "falhou"
                    erro = "Nenhuma conexão WhatsApp ativa"
            except Exception as e:
                status = "falhou"
                erro = str(e)

            # Registrar log
            log = ReminderLog(
                appointment_id=appt.id,
                tipo_lembrete=label,
                status=status,
                erro=erro,
            )
            db.add(log)

        await db.commit()


async def _verificar_ausencias() -> None:
    """Marca como 'faltou' appointments de ontem que não foram realizados."""
    from app.models.appointment import Appointment, AppointmentStatus

    agora = datetime.now(timezone.utc)
    ontem_inicio = agora - timedelta(hours=24)
    ontem_fim = agora - timedelta(hours=1)

    async with _SessionLocal() as db:
        result = await db.execute(
            select(Appointment).where(
                and_(
                    Appointment.data_hora >= ontem_inicio,
                    Appointment.data_hora <= ontem_fim,
                    Appointment.status == AppointmentStatus.agendado,
                )
            )
        )
        appointments = result.scalars().all()
        for appt in appointments:
            appt.status = AppointmentStatus.faltou
        await db.commit()


# ─── Celery tasks ─────────────────────────────────────────────────────────────

def verificar_lembretes_24h() -> None:
    asyncio.run(_enviar_lembrete("24h"))


def verificar_lembretes_2h() -> None:
    asyncio.run(_enviar_lembrete("2h"))


def verificar_ausencias() -> None:
    asyncio.run(_verificar_ausencias())


try:
    from app.workers.celery_app import celery_app
    verificar_lembretes_24h = celery_app.task(
        name="app.workers.reminders.verificar_lembretes_24h"
    )(verificar_lembretes_24h)
    verificar_lembretes_2h = celery_app.task(
        name="app.workers.reminders.verificar_lembretes_2h"
    )(verificar_lembretes_2h)
    verificar_ausencias = celery_app.task(
        name="app.workers.reminders.verificar_ausencias"
    )(verificar_ausencias)
except Exception:
    pass
