"""
Lead Recovery Workers - Recuperação automática de leads inativos
"""

from celery import Celery
from celery.schedules import crontab
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import asyncio
import os

from app.database import AsyncSessionLocal
from app.models.lead_recovery import LeadRecovery, LeadRecoveryTrigger, LeadRecoveryStatus
from app.models.conversation import Conversation, ConversationStatus
from app.models.contact import Contact
from app.models.tenant import Tenant
from app.models.connection import WhatsappConnection
from app.models.message import Message, MessageOrigin, MessageType
from app.models.appointment import Appointment, AppointmentStatus

# Importar celery_app do workers principal
from app.workers import celery_app, run_async


# Configurar task agendada de recuperação
celery_app.conf.beat_schedule.update({
    "verificar-recuperacao-leads": {
        "task": "app.workers.lead_recovery.verificar_recuperacao_leads",
        "schedule": crontab(minute="*/30"),  # A cada 30 minutos
    },
})


# Sequências de recuperação por trigger
RECOVERY_SEQUENCES = {
    LeadRecoveryTrigger.INATIVO: [
        {"delay_hours": 4, "prompt_key": "inativo_tentativa_1"},
        {"delay_hours": 24, "prompt_key": "inativo_tentativa_2"},
        {"delay_hours": 72, "prompt_key": "inativo_tentativa_3"},
    ],
    LeadRecoveryTrigger.FALTOU: [
        {"delay_hours": 2, "prompt_key": "faltou_tentativa_1"},
        {"delay_hours": 24, "prompt_key": "faltou_tentativa_2"},
        {"delay_hours": 72, "prompt_key": "faltou_tentativa_3"},
    ],
    LeadRecoveryTrigger.CANCELOU: [
        {"delay_hours": 1, "prompt_key": "cancelou_tentativa_1"},
        {"delay_hours": 48, "prompt_key": "cancelou_tentativa_2"},
    ],
    LeadRecoveryTrigger.ORCAMENTO: [
        {"delay_hours": 24, "prompt_key": "orcamento_tentativa_1"},
        {"delay_hours": 72, "prompt_key": "orcamento_tentativa_2"},
    ],
}


@celery_app.task(name="app.workers.lead_recovery.verificar_recuperacao_leads")
def verificar_recuperacao_leads():
    """
    Verifica e processa leads em recuperação
    
    Executado a cada 30 minutos
    """
    return run_async(_verificar_recuperacao_leads())


async def _verificar_recuperacao_leads():
    """Implementação assíncrona de verificar_recuperacao_leads"""
    async with AsyncSessionLocal() as db:
        now = datetime.utcnow()
        
        # Buscar leads prontos para próxima tentativa
        result = await db.execute(
            select(LeadRecovery).where(
                and_(
                    LeadRecovery.proxima_tentativa_em <= now,
                    LeadRecovery.status.in_([
                        LeadRecoveryStatus.PENDENTE,
                        LeadRecoveryStatus.EM_ANDAMENTO
                    ])
                )
            )
        )
        leads = result.scalars().all()
        
        print(f"Encontrados {len(leads)} leads para recuperação")
        
        for lead in leads:
            await _processar_tentativa_recuperacao(db, lead)


async def _processar_tentativa_recuperacao(
    db: AsyncSession,
    lead: LeadRecovery
):
    """
    Processa uma tentativa de recuperação
    
    Args:
        db: Sessão do banco
        lead: Lead em recuperação
    """
    try:
        # Incrementar tentativa
        lead.tentativa_atual += 1
        lead.status = LeadRecoveryStatus.EM_ANDAMENTO
        
        # Verificar se atingiu máximo
        if lead.tentativa_atual > lead.max_tentativas:
            await _finalizar_recuperacao(db, lead, sucesso=False)
            return
        
        # Buscar dados relacionados
        result = await db.execute(
            select(Contact).where(Contact.id == lead.contact_id)
        )
        contact = result.scalar_one_or_none()
        
        result = await db.execute(
            select(Tenant).where(Tenant.id == lead.tenant_id)
        )
        tenant = result.scalar_one_or_none()
        
        if not contact or not tenant:
            print(f"Dados incompletos para LeadRecovery {lead.id}")
            return
        
        # Gerar mensagem via LLM
        message_text = await _gerar_mensagem_recuperacao(
            db, lead, contact, tenant
        )
        
        # Enviar mensagem
        await _enviar_mensagem_recuperacao(
            db, lead, contact, tenant, message_text
        )
        
        # Agendar próxima tentativa
        sequence = RECOVERY_SEQUENCES.get(lead.trigger_tipo, [])
        if lead.tentativa_atual < len(sequence):
            next_delay = sequence[lead.tentativa_atual]["delay_hours"]
            lead.proxima_tentativa_em = datetime.utcnow() + timedelta(hours=next_delay)
        else:
            # Última tentativa
            lead.proxima_tentativa_em = None
        
        await db.commit()
        
        print(f"Tentativa {lead.tentativa_atual} enviada para {contact.nome} ({lead.trigger_tipo.value})")
    
    except Exception as e:
        print(f"Erro ao processar recuperação: {str(e)}")
        import traceback
        traceback.print_exc()
        await db.rollback()


async def _gerar_mensagem_recuperacao(
    db: AsyncSession,
    lead: LeadRecovery,
    contact: Contact,
    tenant: Tenant
) -> str:
    """
    Gera mensagem de recuperação via LLM
    
    Args:
        db: Sessão do banco
        lead: Lead em recuperação
        contact: Contato
        tenant: Tenant
    
    Returns:
        Texto da mensagem
    """
    # Buscar histórico da conversa
    historico = []
    if lead.conversation_id:
        result = await db.execute(
            select(Message).where(
                Message.conversation_id == lead.conversation_id
            ).order_by(Message.created_at.desc()).limit(20)
        )
        messages = result.scalars().all()
        historico = [
            {
                "role": "user" if msg.origem == MessageOrigin.CLIENTE else "assistant",
                "content": msg.conteudo
            }
            for msg in reversed(messages)
        ]
    
    # Montar prompt baseado no trigger e tentativa
    sequence = RECOVERY_SEQUENCES.get(lead.trigger_tipo, [])
    if lead.tentativa_atual - 1 < len(sequence):
        prompt_key = sequence[lead.tentativa_atual - 1]["prompt_key"]
    else:
        prompt_key = f"{lead.trigger_tipo.value}_tentativa_final"
    
    # Buscar template do tenant ou usar padrão
    configuracoes = tenant.configuracoes or {}
    prompts_recuperacao = configuracoes.get("prompts_recuperacao", {})
    
    system_prompt = prompts_recuperacao.get(
        prompt_key,
        _get_default_prompt(lead.trigger_tipo, lead.tentativa_atual)
    )
    
    # Adicionar contexto
    context = f"""
Você está fazendo recuperação de lead para a clínica {tenant.nome}.

INFORMAÇÕES DO PACIENTE:
- Nome: {contact.nome or 'Não informado'}
- Telefone: {contact.telefone}

SITUAÇÃO:
- Trigger: {lead.trigger_tipo.value}
- Tentativa: {lead.tentativa_atual} de {lead.max_tentativas}

HISTÓRICO DA CONVERSA ANTERIOR:
{_format_historico(historico)}

{system_prompt}

INSTRUÇÕES IMPORTANTES:
- Seja empático e não insistente
- Não repita a mesma abordagem de tentativas anteriores
- Sempre dê uma saída digna ao paciente
- Mantenha tom profissional mas humanizado
- Máximo 150 caracteres por mensagem
"""
    
    # Chamar LLM
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import SystemMessage
    
    llm = ChatOpenAI(model="gpt-4o", temperature=0.7)
    response = await llm.ainvoke([SystemMessage(content=context)])
    
    return response.content


def _get_default_prompt(trigger: LeadRecoveryTrigger, tentativa: int) -> str:
    """Retorna prompt padrão baseado no trigger e tentativa"""
    prompts = {
        (LeadRecoveryTrigger.INATIVO, 1): """
            Faça um acompanhamento suave perguntando se ainda tem interesse.
            Ofereça ajuda para encontrar um horário conveniente.
        """,
        (LeadRecoveryTrigger.INATIVO, 2): """
            Destaque um benefício específico do procedimento.
            Crie senso de urgência (vagas limitadas, promoção temporária).
            Ofereça um horário específico disponível.
        """,
        (LeadRecoveryTrigger.INATIVO, 3): """
            Última tentativa amigável.
            Deixe porta aberta para futuro contato.
            Se não responder, escalar para atendente humano.
        """,
        (LeadRecoveryTrigger.FALTOU, 1): """
            Demonstre preocupação genuína.
            Pergunte se está tudo bem.
            Ofereça reagendamento sem julgamento.
        """,
        (LeadRecoveryTrigger.FALTOU, 2): """
            Ofereça condição especial (desconto, horário VIP).
            Reforce importância do procedimento para saúde.
        """,
        (LeadRecoveryTrigger.CANCELOU, 1): """
            Tente entender o motivo do cancelamento.
            Ofereça soluções para possíveis objeções.
        """,
        (LeadRecoveryTrigger.CANCELOU, 2): """
            Ofereça alternativas (outro horário, outro profissional).
            Destaque flexibilidade da clínica.
        """,
    }
    
    return prompts.get((trigger, tentativa), "Faça um contato de recuperação empático e profissional.")


def _format_historico(historico: List[Dict[str, str]]) -> str:
    """Formata histórico para o prompt"""
    if not historico:
        return "Sem histórico anterior"
    
    formatted = []
    for msg in historico[-10:]:  # Últimas 10 mensagens
        role = "Paciente" if msg["role"] == "user" else "Atendente"
        formatted.append(f"{role}: {msg['content']}")
    
    return "\n".join(formatted)


async def _enviar_mensagem_recuperacao(
    db: AsyncSession,
    lead: LeadRecovery,
    contact: Contact,
    tenant: Tenant,
    message_text: str
):
    """Envia mensagem de recuperação via WhatsApp"""
    # Buscar conexão WhatsApp ativa
    result = await db.execute(
        select(WhatsappConnection).where(
            and_(
                WhatsappConnection.tenant_id == lead.tenant_id,
                WhatsappConnection.ativo == True
            )
        ).limit(1)
    )
    connection = result.scalar_one_or_none()
    
    if not connection:
        print(f"Sem conexão WhatsApp ativa para tenant {lead.tenant_id}")
        return
    
    # Enviar mensagem
    from app.services.whatsapp.sender import WhatsAppSender
    sender = WhatsAppSender(connection)
    await sender.send(contact.telefone, "text", message=message_text)
    
    # Salvar na conversa
    if lead.conversation_id:
        message = Message(
            conversation_id=lead.conversation_id,
            tenant_id=lead.tenant_id,
            origem=MessageOrigin.AGENTE,
            tipo=MessageType.TEXTO,
            conteudo=message_text,
            metadados={
                "tipo": "recuperacao_lead",
                "lead_recovery_id": lead.id,
                "tentativa": lead.tentativa_atual
            }
        )
        db.add(message)
        await db.commit()


async def _finalizar_recuperacao(
    db: AsyncSession,
    lead: LeadRecovery,
    sucesso: bool
):
    """
    Finaliza processo de recuperação
    
    Args:
        db: Sessão do banco
        lead: Lead em recuperação
        sucesso: Se foi recuperado com sucesso
    """
    if sucesso:
        lead.status = LeadRecoveryStatus.RECUPERADO
        print(f"Lead {lead.id} recuperado com sucesso!")
    else:
        lead.status = LeadRecoveryStatus.DESISTIU
        
        # Escalar para humano
        await _escalar_lead_para_humano(db, lead)
        
        print(f"Lead {lead.id} marcado como desistiu após {lead.tentativa_atual} tentativas")
    
    await db.commit()


async def _escalar_lead_para_humano(
    db: AsyncSession,
    lead: LeadRecovery
):
    """Escala lead para atendimento humano com resumo"""
    if not lead.conversation_id:
        return
    
    # Atualizar conversa
    result = await db.execute(
        select(Conversation).where(Conversation.id == lead.conversation_id)
    )
    conversation = result.scalar_one_or_none()
    
    if conversation:
        conversation.agente_ativo = False
        conversation.status = ConversationStatus.ASSUMIDO
        
        # Notificar via WebSocket
        from app.api.v1.websocket import broadcast_to_tenant
        
        await broadcast_to_tenant(lead.tenant_id, {
            "event": "lead_escalado",
            "conversation_id": conversation.id,
            "lead_recovery_id": lead.id,
            "trigger": lead.trigger_tipo.value,
            "tentativas": lead.tentativa_atual
        })


async def criar_lead_recovery(
    db: AsyncSession,
    tenant_id: int,
    contact_id: int,
    conversation_id: Optional[int],
    trigger_tipo: LeadRecoveryTrigger,
    delay_hours: Optional[int] = None
) -> LeadRecovery:
    """
    Cria novo lead em recuperação
    
    Args:
        db: Sessão do banco
        tenant_id: ID do tenant
        contact_id: ID do contato
        conversation_id: ID da conversa (opcional)
        trigger_tipo: Tipo de trigger
        delay_hours: Delay em horas para primeira tentativa (opcional)
    
    Returns:
        LeadRecovery criado
    """
    # Verificar se já existe recuperação ativa
    result = await db.execute(
        select(LeadRecovery).where(
            and_(
                LeadRecovery.contact_id == contact_id,
                LeadRecovery.status.in_([
                    LeadRecoveryStatus.PENDENTE,
                    LeadRecoveryStatus.EM_ANDAMENTO
                ])
            )
        )
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        print(f"Lead recovery já existe para contact {contact_id}")
        return existing
    
    # Determinar delay
    if delay_hours is None:
        sequence = RECOVERY_SEQUENCES.get(trigger_tipo, [])
        delay_hours = sequence[0]["delay_hours"] if sequence else 4
    
    # Criar lead recovery
    lead = LeadRecovery(
        tenant_id=tenant_id,
        contact_id=contact_id,
        conversation_id=conversation_id,
        trigger_tipo=trigger_tipo,
        status=LeadRecoveryStatus.PENDENTE,
        tentativa_atual=0,
        max_tentativas=len(RECOVERY_SEQUENCES.get(trigger_tipo, [])),
        proxima_tentativa_em=datetime.utcnow() + timedelta(hours=delay_hours)
    )
    
    db.add(lead)
    await db.commit()
    
    print(f"Lead recovery criado: {trigger_tipo.value} para contact {contact_id}")
    
    return lead


async def cancelar_lead_recovery(
    db: AsyncSession,
    contact_id: int
) -> bool:
    """
    Cancela recuperação ativa (quando cliente responde)
    
    Args:
        db: Sessão do banco
        contact_id: ID do contato
    
    Returns:
        True se cancelou alguma recuperação
    """
    result = await db.execute(
        select(LeadRecovery).where(
            and_(
                LeadRecovery.contact_id == contact_id,
                LeadRecovery.status.in_([
                    LeadRecoveryStatus.PENDENTE,
                    LeadRecoveryStatus.EM_ANDAMENTO
                ])
            )
        )
    )
    lead = result.scalar_one_or_none()
    
    if lead:
        lead.status = LeadRecoveryStatus.RECUPERADO
        await db.commit()
        print(f"Lead recovery cancelado (recuperado) para contact {contact_id}")
        return True
    
    return False
