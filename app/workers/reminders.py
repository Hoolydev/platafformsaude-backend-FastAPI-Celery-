"""
Reminder Workers - Lembretes automáticos de agendamento
"""

from celery import Celery
from celery.schedules import crontab
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Dict, Any, List
from datetime import datetime, timedelta
import asyncio
import os

from app.database import AsyncSessionLocal
from app.models.appointment import Appointment, AppointmentStatus
from app.models.reminder_log import ReminderLog, ReminderType, ReminderStatus
from app.models.contact import Contact
from app.models.procedure import Procedure
from app.models.tenant import Tenant
from app.models.connection import WhatsappConnection
from app.models.message import Message, MessageOrigin, MessageType
from app.models.conversation import Conversation, ConversationStatus

# Importar celery_app do workers principal
from app.workers import celery_app, run_async


# Configurar tasks agendadas de lembretes
celery_app.conf.beat_schedule.update({
    "verificar-lembretes-24h": {
        "task": "app.workers.reminders.verificar_lembretes_24h",
        "schedule": crontab(minute="0"),  # A cada hora
    },
    "verificar-lembretes-2h": {
        "task": "app.workers.reminders.verificar_lembretes_2h",
        "schedule": crontab(minute="*/15"),  # A cada 15 minutos
    },
    "verificar-ausencias": {
        "task": "app.workers.reminders.verificar_ausencias",
        "schedule": crontab(hour=10, minute=0),  # Diariamente às 10h
    },
})


@celery_app.task(name="app.workers.reminders.verificar_lembretes_24h")
def verificar_lembretes_24h():
    """
    Verifica e envia lembretes 24 horas antes da consulta
    
    Executado a cada hora
    """
    return run_async(_verificar_lembretes_24h())


async def _verificar_lembretes_24h():
    """Implementação assíncrona de verificar_lembretes_24h"""
    async with AsyncSessionLocal() as db:
        # Buscar agendamentos em 24h ±10min
        now = datetime.utcnow()
        target_time = now + timedelta(hours=24)
        time_window_start = target_time - timedelta(minutes=10)
        time_window_end = target_time + timedelta(minutes=10)
        
        result = await db.execute(
            select(Appointment).where(
                and_(
                    Appointment.data_hora >= time_window_start,
                    Appointment.data_hora <= time_window_end,
                    Appointment.status.in_([AppointmentStatus.AGENDADO, AppointmentStatus.CONFIRMADO])
                )
            )
        )
        appointments = result.scalars().all()
        
        print(f"Encontrados {len(appointments)} agendamentos para lembrete 24h")
        
        for appointment in appointments:
            await _enviar_lembrete(db, appointment, ReminderType.LEMBRETE_24H)


@celery_app.task(name="app.workers.reminders.verificar_lembretes_2h")
def verificar_lembretes_2h():
    """
    Verifica e envia lembretes 2 horas antes da consulta
    
    Executado a cada 15 minutos
    """
    return run_async(_verificar_lembretes_2h())


async def _verificar_lembretes_2h():
    """Implementação assíncrona de verificar_lembretes_2h"""
    async with AsyncSessionLocal() as db:
        # Buscar agendamentos em 2h ±5min
        now = datetime.utcnow()
        target_time = now + timedelta(hours=2)
        time_window_start = target_time - timedelta(minutes=5)
        time_window_end = target_time + timedelta(minutes=5)
        
        result = await db.execute(
            select(Appointment).where(
                and_(
                    Appointment.data_hora >= time_window_start,
                    Appointment.data_hora <= time_window_end,
                    Appointment.status.in_([AppointmentStatus.AGENDADO, AppointmentStatus.CONFIRMADO])
                )
            )
        )
        appointments = result.scalars().all()
        
        print(f"Encontrados {len(appointments)} agendamentos para lembrete 2h")
        
        for appointment in appointments:
            await _enviar_lembrete(db, appointment, ReminderType.LEMBRETE_2H)


@celery_app.task(name="app.workers.reminders.verificar_ausencias")
def verificar_ausencias():
    """
    Verifica ausências e marca como "faltou"
    
    Executado diariamente às 10h
    """
    return run_async(_verificar_ausencias())


async def _verificar_ausencias():
    """Implementação assíncrona de verificar_ausencias"""
    async with AsyncSessionLocal() as db:
        # Buscar agendamentos passados sem confirmação
        now = datetime.utcnow()
        
        result = await db.execute(
            select(Appointment).where(
                and_(
                    Appointment.data_hora < now,
                    Appointment.status == AppointmentStatus.AGENDADO
                )
            )
        )
        appointments = result.scalars().all()
        
        print(f"Encontrados {len(appointments)} agendamentos com ausência")
        
        for appointment in appointments:
            # Marcar como faltou
            appointment.status = AppointmentStatus.FALTOU
            
            # Criar lead recovery para recuperação
            from app.workers.lead_recovery import criar_lead_recovery
            from app.models.lead_recovery import LeadRecoveryTrigger
            
            await criar_lead_recovery(
                db,
                tenant_id=appointment.tenant_id,
                contact_id=appointment.contact_id,
                conversation_id=None,  # Não há conversa específica
                trigger_tipo=LeadRecoveryTrigger.FALTOU,
                delay_hours=2  # Primeira tentativa em 2h
            )
            
            print(f"Marcado como faltou e criado lead recovery: Appointment {appointment.id}")
        
        await db.commit()


async def _enviar_lembrete(
    db: AsyncSession,
    appointment: Appointment,
    tipo_lembrete: ReminderType
):
    """
    Envia lembrete para um agendamento
    
    Args:
        db: Sessão do banco
        appointment: Agendamento
        tipo_lembrete: Tipo do lembrete
    """
    # Verificar se já foi enviado
    result = await db.execute(
        select(ReminderLog).where(
            and_(
                ReminderLog.appointment_id == appointment.id,
                ReminderLog.tipo_lembrete == tipo_lembrete,
                ReminderLog.status == ReminderStatus.ENVIADO
            )
        )
    )
    existing_log = result.scalar_one_or_none()
    
    if existing_log:
        print(f"Lembrete {tipo_lembrete.value} já enviado para Appointment {appointment.id}")
        return
    
    try:
        # Buscar dados relacionados
        result = await db.execute(
            select(Contact).where(Contact.id == appointment.contact_id)
        )
        contact = result.scalar_one_or_none()
        
        result = await db.execute(
            select(Procedure).where(Procedure.id == appointment.procedure_id)
        )
        procedure = result.scalar_one_or_none()
        
        result = await db.execute(
            select(Tenant).where(Tenant.id == appointment.tenant_id)
        )
        tenant = result.scalar_one_or_none()
        
        if not contact or not procedure or not tenant:
            print(f"Dados incompletos para Appointment {appointment.id}")
            return
        
        # Buscar template de mensagem
        template = _get_message_template(tenant, tipo_lembrete)
        
        # Personalizar mensagem
        message_text = _personalize_message(
            template,
            contact,
            procedure,
            appointment,
            tenant
        )
        
        # Buscar conexão WhatsApp ativa
        result = await db.execute(
            select(WhatsappConnection).where(
                and_(
                    WhatsappConnection.tenant_id == appointment.tenant_id,
                    WhatsappConnection.ativo == True
                )
            ).limit(1)
        )
        connection = result.scalar_one_or_none()
        
        if not connection:
            print(f"Sem conexão WhatsApp ativa para tenant {appointment.tenant_id}")
            return
        
        # Enviar mensagem
        from app.services.whatsapp.sender import WhatsAppSender
        sender = WhatsAppSender(connection)
        await sender.send(contact.telefone, "text", message=message_text)
        
        # Salvar na memória do agente (tabela messages)
        await _save_to_agent_memory(db, appointment, contact, message_text)
        
        # Criar log de lembrete
        reminder_log = ReminderLog(
            appointment_id=appointment.id,
            tipo_lembrete=tipo_lembrete,
            status=ReminderStatus.ENVIADO,
            enviado_em=datetime.utcnow()
        )
        db.add(reminder_log)
        await db.commit()
        
        print(f"Lembrete {tipo_lembrete.value} enviado para {contact.nome} ({contact.telefone})")
    
    except Exception as e:
        print(f"Erro ao enviar lembrete: {str(e)}")
        
        # Criar log de erro
        reminder_log = ReminderLog(
            appointment_id=appointment.id,
            tipo_lembrete=tipo_lembrete,
            status=ReminderStatus.ERRO,
            erro=str(e)
        )
        db.add(reminder_log)
        await db.commit()


def _get_message_template(tenant: Tenant, tipo_lembrete: ReminderType) -> str:
    """Busca template de mensagem nas configurações do tenant"""
    configuracoes = tenant.configuracoes or {}
    
    templates = {
        ReminderType.CONFIRMACAO: configuracoes.get(
            "lembrete_confirmacao",
            "Agendamento confirmado! ✅ {procedimento} em {data} às {hora}."
        ),
        ReminderType.LEMBRETE_24H: configuracoes.get(
            "lembrete_24h",
            "Olá {nome}! 👋 Lembrando que você tem {procedimento} amanhã às {hora}. Confirme com SIM ou cancele com NÃO."
        ),
        ReminderType.LEMBRETE_2H: configuracoes.get(
            "lembrete_2h",
            "Olá {nome}! Sua consulta é em 2 horas ({hora}). Estamos te esperando! 🏥"
        )
    }
    
    return templates.get(tipo_lembrete, "Lembrete de consulta: {procedimento} em {data} às {hora}")


def _personalize_message(
    template: str,
    contact: Contact,
    procedure: Procedure,
    appointment: Appointment,
    tenant: Tenant
) -> str:
    """Personaliza template com dados do agendamento"""
    data_hora = appointment.data_hora
    
    # Formatar data e hora
    data_formatada = data_hora.strftime("%d/%m/%Y")
    hora_formatada = data_hora.strftime("%H:%M")
    
    # Substituir placeholders
    message = template.format(
        nome=contact.nome or "Paciente",
        procedimento=procedure.nome,
        data=data_formatada,
        hora=hora_formatada,
        endereco=tenant.configuracoes.get("endereco", "") if tenant.configuracoes else "",
        link=tenant.configuracoes.get("link_maps", "") if tenant.configuracoes else ""
    )
    
    return message


async def _save_to_agent_memory(
    db: AsyncSession,
    appointment: Appointment,
    contact: Contact,
    message_text: str
):
    """Salva lembrete na memória do agente (tabela messages)"""
    # Buscar ou criar conversa
    result = await db.execute(
        select(Conversation).where(
            and_(
                Conversation.tenant_id == appointment.tenant_id,
                Conversation.contact_id == contact.id,
                Conversation.status.in_([ConversationStatus.ATIVO, ConversationStatus.ASSUMIDO])
            )
        ).order_by(Conversation.created_at.desc()).limit(1)
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        # Criar nova conversa
        conversation = Conversation(
            tenant_id=appointment.tenant_id,
            contact_id=contact.id,
            canal="whatsapp",
            status=ConversationStatus.ATIVO,
            agente_ativo=False
        )
        db.add(conversation)
        await db.flush()
    
    # Salvar mensagem
    message = Message(
        conversation_id=conversation.id,
        tenant_id=appointment.tenant_id,
        origem=MessageOrigin.AGENTE,
        tipo=MessageType.TEXTO,
        conteudo=message_text,
        metadados={
            "tipo": "lembrete_agendamento",
            "appointment_id": appointment.id
        }
    )
    db.add(message)
    await db.commit()


@celery_app.task(name="app.workers.reminders.enviar_confirmacao_imediata")
def enviar_confirmacao_imediata(appointment_id: int):
    """
    Envia confirmação imediata após criar agendamento
    
    Args:
        appointment_id: ID do agendamento
    """
    return run_async(_enviar_confirmacao_imediata(appointment_id))


async def _enviar_confirmacao_imediata(appointment_id: int):
    """Implementação assíncrona de enviar_confirmacao_imediata"""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Appointment).where(Appointment.id == appointment_id)
        )
        appointment = result.scalar_one_or_none()
        
        if appointment:
            await _enviar_lembrete(db, appointment, ReminderType.CONFIRMACAO)


async def processar_resposta_lembrete(
    db: AsyncSession,
    tenant_id: int,
    contact_id: int,
    message_text: str
) -> bool:
    """
    Processa resposta do paciente ao lembrete
    
    Args:
        db: Sessão do banco
        tenant_id: ID do tenant
        contact_id: ID do contato
        message_text: Texto da mensagem
    
    Returns:
        True se processou como resposta a lembrete, False caso contrário
    """
    message_lower = message_text.lower().strip()
    
    # Verificar se é SIM ou NÃO
    if message_lower not in ["sim", "não", "nao", "yes", "no"]:
        return False
    
    # Buscar último agendamento do contato
    result = await db.execute(
        select(Appointment).where(
            and_(
                Appointment.tenant_id == tenant_id,
                Appointment.contact_id == contact_id,
                Appointment.status.in_([AppointmentStatus.AGENDADO, AppointmentStatus.CONFIRMADO]),
                Appointment.data_hora > datetime.utcnow()
            )
        ).order_by(Appointment.data_hora.asc()).limit(1)
    )
    appointment = result.scalar_one_or_none()
    
    if not appointment:
        return False
    
    # Processar resposta
    if message_lower in ["sim", "yes"]:
        # Confirmar agendamento
        appointment.status = AppointmentStatus.CONFIRMADO
        await db.commit()
        
        # Enviar confirmação
        response = "✅ Agendamento confirmado! Obrigado. Te esperamos no horário marcado."
        return True
    
    elif message_lower in ["não", "nao", "no"]:
        # Iniciar fluxo de cancelamento
        appointment.status = AppointmentStatus.CANCELADO
        await db.commit()
        
        # TODO: Oferecer reagendamento
        response = "Agendamento cancelado. Gostaria de reagendar para outro horário?"
        return True
    
    return False
