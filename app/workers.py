"""
Celery Workers - Tarefas assíncronas e agendadas
"""

from celery import Celery
from celery.schedules import crontab
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any, Optional
import asyncio
import os
import json
from datetime import datetime, timedelta

from app.database import AsyncSessionLocal
from app.models.contact import Contact
from app.models.conversation import Conversation, ConversationStatus
from app.models.message import Message, MessageOrigin, MessageType
from app.models.agent import Agent
from app.models.connection import WhatsappConnection

# Configurar Celery
celery_app = Celery(
    "saude_platform",
    broker=os.getenv("CELERY_BROKER_URL", "redis://:RedisSecurePass2024!@redis:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://:RedisSecurePass2024!@redis:6379/0")
)

# Configurações
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Sao_Paulo",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutos
    task_soft_time_limit=240,  # 4 minutos
)

# Tarefas agendadas
celery_app.conf.beat_schedule = {
    "check-follow-ups": {
        "task": "app.workers.check_follow_ups",
        "schedule": crontab(minute="*/30"),  # A cada 30 minutos
    },
    "send-daily-reports": {
        "task": "app.workers.send_daily_reports",
        "schedule": crontab(hour=9, minute=0),  # 9h da manhã
    },
}


def run_async(coro):
    """Helper para executar coroutines assíncronas em tasks Celery"""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)


@celery_app.task(name="app.workers.process_incoming_message")
def process_incoming_message(tenant_id: int, message_data: Dict[str, Any]):
    """
    Processa mensagem recebida via webhook
    
    1. Buscar ou criar Contact
    2. Buscar ou criar Conversation
    3. Salvar Message
    4. Verificar se agente está ativo
    5. Se ativo: processar com agente IA
    6. Se não: notificar atendentes via WebSocket
    """
    return run_async(_process_incoming_message(tenant_id, message_data))


async def _process_incoming_message(tenant_id: int, message_data: Dict[str, Any]):
    """Implementação assíncrona do processamento de mensagem"""
    async with AsyncSessionLocal() as db:
        try:
            telefone = message_data["telefone"]
            nome_contato = message_data.get("nome_contato")
            
            # 1. Buscar ou criar Contact
            result = await db.execute(
                select(Contact).where(
                    Contact.tenant_id == tenant_id,
                    Contact.telefone == telefone
                )
            )
            contact = result.scalar_one_or_none()
            
            if not contact:
                contact = Contact(
                    tenant_id=tenant_id,
                    telefone=telefone,
                    nome=nome_contato,
                    metadados={}
                )
                db.add(contact)
                await db.flush()
            elif nome_contato and not contact.nome:
                # Atualizar nome se não existir
                contact.nome = nome_contato
            
            # 2. Verificar se é resposta a lembrete (SIM/NÃO)
            from app.workers.reminders import processar_resposta_lembrete
            
            message_text = message_data.get("conteudo", "")
            is_reminder_response = await processar_resposta_lembrete(
                db, tenant_id, contact.id, message_text
            )
            
            if is_reminder_response:
                # Já foi processado como resposta a lembrete
                return {"status": "processed_as_reminder_response"}
            
            # 3. Buscar ou criar Conversation ativa
            result = await db.execute(
                select(Conversation).where(
                    Conversation.tenant_id == tenant_id,
                    Conversation.contact_id == contact.id,
                    Conversation.status.in_([ConversationStatus.ATIVO, ConversationStatus.ASSUMIDO])
                ).order_by(Conversation.created_at.desc())
            )
            conversation = result.scalar_one_or_none()
            
            if not conversation:
                # Criar nova conversa
                # Buscar agente padrão do tenant (primeiro ativo)
                result = await db.execute(
                    select(Agent).where(
                        Agent.tenant_id == tenant_id,
                        Agent.ativo == True
                    ).limit(1)
                )
                default_agent = result.scalar_one_or_none()
                
                conversation = Conversation(
                    tenant_id=tenant_id,
                    contact_id=contact.id,
                    canal=message_data.get("provider", "whatsapp"),
                    status=ConversationStatus.ATIVO,
                    agente_ativo=True if default_agent else False,
                    agent_id=default_agent.id if default_agent else None
                )
                db.add(conversation)
                await db.flush()
            
            # 4. Salvar mensagem
            message = Message(
                conversation_id=conversation.id,
                tenant_id=tenant_id,
                origem=MessageOrigin.CLIENTE,
                tipo=MessageType[message_data["tipo_mensagem"].upper()],
                conteudo=message_data["conteudo"],
                metadados={
                    "midia_url": message_data.get("midia_url"),
                    "mimetype": message_data.get("mimetype"),
                    "provider": message_data.get("provider")
                },
                external_id=message_data.get("external_id")
            )
            db.add(message)
            # 4. Verificar se agente está ativo
            if conversation.agente_ativo and conversation.agent_id:
                # 5. Processar com agente IA
                await _process_with_agent(
                    db, tenant_id, conversation, message, message_data
                )
            else:
                # 6. Notificar atendentes via WebSocket
                await _notify_attendants(tenant_id, conversation.id, message.id)
            
            return {"status": "processed", "conversation_id": conversation.id}
        
        except Exception as e:
            print(f"Erro ao processar mensagem: {str(e)}")
            await db.rollback()
            raise


async def _verificar_lead_inativo(
    db: AsyncSession,
    conversation: Conversation,
    contact: Contact,
    tenant_id: int
):
    """
    Verifica se conversa está inativa e cria lead recovery se necessário
    
    Args:
        db: Sessão do banco
        conversation: Conversa
        contact: Contato
        tenant_id: ID do tenant
    """
    from app.models.appointment import Appointment, AppointmentStatus
    from app.workers.lead_recovery import criar_lead_recovery
    from app.models.lead_recovery import LeadRecoveryTrigger
    from app.models.tenant import Tenant
    
    # Buscar configuração de tempo de inatividade
    result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        return
    
    configuracoes = tenant.configuracoes or {}
    horas_inatividade = configuracoes.get("horas_inatividade_lead", 4)
    
    # Verificar se conversa tem agendamento
    result = await db.execute(
        select(Appointment).where(
            and_(
                Appointment.conversation_id == conversation.id,
                Appointment.status.in_([
                    AppointmentStatus.AGENDADO,
                    AppointmentStatus.CONFIRMADO,
                    AppointmentStatus.REALIZADO
                ])
            )
        )
    )
    has_appointment = result.scalar_one_or_none() is not None
    
    # Se já tem agendamento, não é lead inativo
    if has_appointment:
        return
    
    # Verificar tempo desde criação da conversa
    now = datetime.utcnow()
    tempo_decorrido = now - conversation.created_at
    
    # Se passou do tempo configurado, criar lead recovery
    if tempo_decorrido.total_seconds() > (horas_inatividade * 3600):
        await criar_lead_recovery(
            db,
            tenant_id=tenant_id,
            contact_id=contact.id,
            conversation_id=conversation.id,
            trigger_tipo=LeadRecoveryTrigger.INATIVO,
            delay_hours=horas_inatividade
        )


async def _process_with_agent(
    db: AsyncSession,
    tenant_id: int,
    conversation: Conversation,
    message: Message,
    message_data: Dict[str, Any]
):
    """
    Processa mensagem com agente IA usando LangGraph
    """
    # Buscar agente
    result = await db.execute(
        select(Agent).where(Agent.id == conversation.agent_id)
    )
    agent = result.scalar_one_or_none()
    
    if not agent:
        return
    
    # Preparar configuração do agente
    agent_config = {
        "instrucoes": agent.instrucoes,
        "modelo": agent.modelo_llm,
        "temperatura": agent.temperatura,
        "ferramentas_ativas": [tool.nome for tool in agent.tools],
        "voz": {
            "ativo": agent.voz_ativa,
            "voice_id": agent.voz_id
        }
    }
    
    # Preparar mensagem
    incoming_message = {
        "tipo": message_data.get("tipo_mensagem"),
        "conteudo": message_data.get("conteudo"),
        "metadados": {
            "midia_url": message_data.get("midia_url"),
            "mimetype": message_data.get("mimetype")
        }
    }
    
    # Processar com engine de IA
    from app.agents.engine import process_message_with_agent
    
    try:
        result = await process_message_with_agent(
            db=db,
            tenant_id=tenant_id,
            conversation_id=conversation.id,
            contact_id=conversation.contact_id,
            agent_config=agent_config,
            message=incoming_message
        )
        
        # Verificar se deve escalar
        if result.get("deve_escalar"):
            # Escalar para humano
            conversation.agente_ativo = False
            conversation.status = ConversationStatus.ASSUMIDO
            await db.commit()
            
            # Notificar via WebSocket
            await _notify_attendants(tenant_id, conversation.id, message.id)
            return
        
        # Enviar mensagens geradas pelo agente
        mensagens = result.get("mensagens", [])
        connection_id = message_data.get("connection_id")
        telefone = message_data.get("telefone")
        
        for msg_part in mensagens:
            # Salvar mensagem do agente no banco
            agent_message = Message(
                conversation_id=conversation.id,
                tenant_id=tenant_id,
                origem=MessageOrigin.AGENTE,
                tipo=MessageType.TEXTO if msg_part.get("tipo") == "text" else MessageType.AUDIO,
                conteudo=msg_part["conteudo"],
                metadados={
                    "agent_id": agent.id,
                    "delay_ms": msg_part.get("delay_ms"),
                    "audio_base64": msg_part.get("audio_base64")
                }
            )
            db.add(agent_message)
            await db.flush()
            
            # Aguardar delay de digitação
            delay_seconds = msg_part.get("delay_ms", 0) / 1000
            if delay_seconds > 0:
                import asyncio
                await asyncio.sleep(delay_seconds)
            
            # Enviar via WhatsApp
        print(f"Agente {agent.nome} processou mensagem e enviou {len(mensagens)} respostas")
    
    except Exception as e:
        print(f"Erro ao processar com agente IA: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Em caso de erro, escalar para humano
        conversation.agente_ativo = False
        await db.commit()
        await _notify_attendants(tenant_id, conversation.id, message.id)


async def _send_whatsapp_message(
    tenant_id: int,
    connection_id: int,
    phone: str,
    text: Optional[str] = None,
    message_type: str = "text",
    **kwargs
):
    """Envia mensagem via WhatsApp"""
    try:
        async with AsyncSessionLocal() as db:
            # Buscar conexão
            result = await db.execute(
                select(WhatsappConnection).where(
                    WhatsappConnection.id == connection_id,
                    WhatsappConnection.tenant_id == tenant_id
                )
            )
            connection = result.scalar_one_or_none()
            
            if not connection:
                print(f"Conexão {connection_id} não encontrada")
                return
            
            # Enviar mensagem
            from app.services.whatsapp.sender import WhatsAppSender
            sender = WhatsAppSender(connection)
            
            if message_type == "text":
                await sender.send(phone, "text", message=text)
            elif message_type == "audio":
                audio_base64 = kwargs.get("audio_base64")
                if audio_base64:
                    await sender.send(phone, "audio", audio_base64=audio_base64)
            
            print(f"Mensagem enviada para {phone}")
    
    except Exception as e:
        print(f"Erro ao enviar mensagem WhatsApp: {str(e)}")


async def _notify_attendants(tenant_id: int, conversation_id: int, message_id: int):
    """
    Notifica atendentes via WebSocket sobre nova mensagem
    
    TODO: Implementar broadcast via WebSocket
    """
    # Broadcast para todos os atendentes conectados do tenant
    from app.api.v1.websocket import broadcast_to_tenant
    
    await broadcast_to_tenant(tenant_id, {
        "event": "nova_mensagem",
        "conversation_id": conversation_id,
        "message_id": message_id
    })


@celery_app.task(name="app.workers.check_follow_ups")
def check_follow_ups():
    """
    Verifica conversas que precisam de follow-up
    
    Executado a cada 30 minutos
    """
    return run_async(_check_follow_ups())


async def _check_follow_ups():
    """Implementação assíncrona de check_follow_ups"""
    async with AsyncSessionLocal() as db:
        # Buscar conversas concluídas há mais de 24h sem follow-up
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        result = await db.execute(
            select(Conversation).where(
                Conversation.status == ConversationStatus.CONCLUIDO,
                Conversation.updated_at < cutoff_time
            )
        )
        conversations = result.scalars().all()
        
        print(f"Encontradas {len(conversations)} conversas para follow-up")
        
        # TODO: Implementar lógica de follow-up
        # - Enviar mensagem automática
        # - Pesquisa de satisfação
        # - Lembrete de retorno


@celery_app.task(name="app.workers.send_daily_reports")
def send_daily_reports():
    """
    Envia relatórios diários para admins
    
    Executado às 9h da manhã
    """
    return run_async(_send_daily_reports())


async def _send_daily_reports():
    """Implementação assíncrona de send_daily_reports"""
    print("Enviando relatórios diários...")
    
    # TODO: Implementar
    # - Estatísticas de conversas
    # - Mensagens processadas
    # - Performance dos agentes
    # - Enviar por email


@celery_app.task(name="app.workers.process_prescription")
def process_prescription(tenant_id: int, image_url: str):
    """
    Processa receita médica com OCR/IA
    
    TODO: Implementar
    """
    print(f"Processando receita: {image_url}")
    # - Fazer OCR da imagem
    # - Extrair medicamentos
    # - Validar com IA
    # - Retornar dados estruturados


async def _should_respond_audio(
    db: AsyncSession,
    conversation: Conversation,
    contact: Contact,
    message_data: Dict[str, Any]
) -> bool:
    """
    Verifica se deve responder em áudio
    
    Args:
        db: Sessão do banco
        conversation: Conversa
        contact: Contato
        message_data: Dados da mensagem
    
    Returns:
        True se deve responder em áudio
    """
    from app.models.connection import WhatsappConnection
    
    # Buscar configuração da conexão
    result = await db.execute(
        select(WhatsappConnection).where(
            WhatsappConnection.tenant_id == conversation.tenant_id
        ).limit(1)
    )
    connection = result.scalar_one_or_none()
    
    if not connection or connection.modo_voz != "apenas_audio":
        return False
    
    # Verificar preferência do contato
    metadados = contact.metadados or {}
    preferencia_voz = metadados.get("preferencia_voz")
    
    # Se tem preferência definida, usar ela
    if preferencia_voz is not None:
        return preferencia_voz
    
    # Se cliente enviou áudio, responder em áudio
    if message_data.get("tipo_mensagem") == "audio":
        return True
    
    return False


async def _send_audio_responses(
    db: AsyncSession,
    tenant_id: int,
    conversation: Conversation,
    contact: Contact,
    response_data: List[Dict[str, Any]]
):
    """
    Envia respostas em áudio via ElevenLabs
    
    Args:
        db: Sessão do banco
        tenant_id: ID do tenant
        conversation: Conversa
        contact: Contato
        response_data: Lista de respostas
    """
    from app.integrations.voice import ElevenLabsSender
    from app.models.connection import WhatsappConnection
    
    # Buscar configuração
    result = await db.execute(
        select(WhatsappConnection).where(
            WhatsappConnection.tenant_id == tenant_id
        ).limit(1)
    )
    connection = result.scalar_one_or_none()
    
    if not connection or not connection.elevenlabs_voice_id:
        print("Sem configuração de voz ElevenLabs")
        return
    
    sender = ElevenLabsSender()
    
    for response_msg in response_data:
        text = response_msg.get("conteudo", "")
        
        if not text:
            continue
        
        try:
            # Gerar áudio
            result = await sender.text_to_speech(
                text=text,
                voice_id=connection.elevenlabs_voice_id,
                tenant_id=tenant_id
            )
            
            audio_url = result["audio_url"]
            
            # Enviar como mensagem de áudio
            await _send_whatsapp_message(
                connection_id=connection.id,
                phone=contact.telefone,
                message_type="audio",
                content={"midia_url": audio_url}
            )
            
            # Delay entre mensagens
            delay_ms = response_msg.get("delay_ms", 1000)
            await asyncio.sleep(delay_ms / 1000)
        
        except Exception as e:
            print(f"Erro ao enviar áudio: {str(e)}")
            # Fallback para texto
            await _send_whatsapp_message(
                connection_id=connection.id,
                phone=contact.telefone,
                message_type="text",
                content={"message": text}
            )
