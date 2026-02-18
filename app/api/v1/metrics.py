"""
Metrics Endpoints - Dashboard Analytics
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from datetime import datetime, timedelta
from typing import Optional, List
from pydantic import BaseModel

from app.database import get_db
from app.auth.dependencies import get_current_tenant
from app.models.conversation import Conversation, ConversationStatus
from app.models.appointment import Appointment, AppointmentStatus
from app.models.message import Message, MessageOrigin
from app.models.lead_recovery import LeadRecovery, LeadRecoveryStatus
from app.models.procedure import Procedure


router = APIRouter(prefix="/metrics", tags=["Metrics"])


# Schemas
class MetricsOverview(BaseModel):
    total_conversas: int
    conversas_ativas: int
    conversas_concluidas: int
    total_agendamentos: int
    agendamentos_confirmados: int
    taxa_confirmacao: float
    leads_recuperados: int
    taxa_recuperacao: float
    tempo_medio_resposta_segundos: float
    mensagens_enviadas_agente: int
    mensagens_enviadas_humano: int


class ConversationsByDay(BaseModel):
    data: str
    total: int
    agendadas: int
    canceladas: int
    faltaram: int


class TopProcedure(BaseModel):
    id: int
    nome: str
    total_agendamentos: int


class AgentPerformance(BaseModel):
    taxa_escalacao: float
    taxa_agendamento: float
    tempo_medio_resolucao_minutos: float


def _parse_periodo(periodo: str) -> datetime:
    """Parse período string para datetime"""
    now = datetime.utcnow()
    
    if periodo == "hoje":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif periodo.endswith("d"):
        days = int(periodo[:-1])
        return now - timedelta(days=days)
    elif periodo.endswith("h"):
        hours = int(periodo[:-1])
        return now - timedelta(hours=hours)
    else:
        return now - timedelta(days=7)


@router.get("/overview", response_model=MetricsOverview)
async def get_metrics_overview(
    periodo: str = Query("7d", description="Período: hoje, 7d, 30d, etc"),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    Retorna métricas gerais do período
    """
    start_date = _parse_periodo(periodo)
    
    # Total de conversas
    result = await db.execute(
        select(func.count(Conversation.id)).where(
            and_(
                Conversation.tenant_id == tenant_id,
                Conversation.created_at >= start_date
            )
        )
    )
    total_conversas = result.scalar() or 0
    
    # Conversas ativas
    result = await db.execute(
        select(func.count(Conversation.id)).where(
            and_(
                Conversation.tenant_id == tenant_id,
                Conversation.status == ConversationStatus.ATIVO,
                Conversation.created_at >= start_date
            )
        )
    )
    conversas_ativas = result.scalar() or 0
    
    # Conversas concluídas
    result = await db.execute(
        select(func.count(Conversation.id)).where(
            and_(
                Conversation.tenant_id == tenant_id,
                Conversation.status == ConversationStatus.CONCLUIDO,
                Conversation.created_at >= start_date
            )
        )
    )
    conversas_concluidas = result.scalar() or 0
    
    # Total de agendamentos
    result = await db.execute(
        select(func.count(Appointment.id)).where(
            and_(
                Appointment.tenant_id == tenant_id,
                Appointment.created_at >= start_date
            )
        )
    )
    total_agendamentos = result.scalar() or 0
    
    # Agendamentos confirmados
    result = await db.execute(
        select(func.count(Appointment.id)).where(
            and_(
                Appointment.tenant_id == tenant_id,
                Appointment.status == AppointmentStatus.CONFIRMADO,
                Appointment.created_at >= start_date
            )
        )
    )
    agendamentos_confirmados = result.scalar() or 0
    
    # Taxa de confirmação
    taxa_confirmacao = (
        (agendamentos_confirmados / total_agendamentos * 100)
        if total_agendamentos > 0 else 0
    )
    
    # Leads recuperados
    result = await db.execute(
        select(func.count(LeadRecovery.id)).where(
            and_(
                LeadRecovery.tenant_id == tenant_id,
                LeadRecovery.status == LeadRecoveryStatus.RECUPERADO,
                LeadRecovery.created_at >= start_date
            )
        )
    )
    leads_recuperados = result.scalar() or 0
    
    # Total de leads
    result = await db.execute(
        select(func.count(LeadRecovery.id)).where(
            and_(
                LeadRecovery.tenant_id == tenant_id,
                LeadRecovery.created_at >= start_date
            )
        )
    )
    total_leads = result.scalar() or 0
    
    # Taxa de recuperação
    taxa_recuperacao = (
        (leads_recuperados / total_leads * 100)
        if total_leads > 0 else 0
    )
    
    # Tempo médio de resposta (em segundos)
    # Calcular diferença entre mensagem do cliente e resposta do agente
    result = await db.execute(
        select(
            func.avg(
                func.extract('epoch', Message.created_at) - 
                func.extract('epoch', func.lag(Message.created_at).over(
                    partition_by=Message.conversation_id,
                    order_by=Message.created_at
                ))
            )
        ).where(
            and_(
                Message.tenant_id == tenant_id,
                Message.origem == MessageOrigin.AGENTE,
                Message.created_at >= start_date
            )
        )
    )
    tempo_medio_resposta = result.scalar() or 0
    
    # Mensagens enviadas por agente
    result = await db.execute(
        select(func.count(Message.id)).where(
            and_(
                Message.tenant_id == tenant_id,
                Message.origem == MessageOrigin.AGENTE,
                Message.created_at >= start_date
            )
        )
    )
    mensagens_agente = result.scalar() or 0
    
    # Mensagens enviadas por humano
    result = await db.execute(
        select(func.count(Message.id)).where(
            and_(
                Message.tenant_id == tenant_id,
                Message.origem == MessageOrigin.HUMANO,
                Message.created_at >= start_date
            )
        )
    )
    mensagens_humano = result.scalar() or 0
    
    return MetricsOverview(
        total_conversas=total_conversas,
        conversas_ativas=conversas_ativas,
        conversas_concluidas=conversas_concluidas,
        total_agendamentos=total_agendamentos,
        agendamentos_confirmados=agendamentos_confirmados,
        taxa_confirmacao=round(taxa_confirmacao, 2),
        leads_recuperados=leads_recuperados,
        taxa_recuperacao=round(taxa_recuperacao, 2),
        tempo_medio_resposta_segundos=round(tempo_medio_resposta, 2),
        mensagens_enviadas_agente=mensagens_agente,
        mensagens_enviadas_humano=mensagens_humano
    )


@router.get("/conversations-by-day", response_model=List[ConversationsByDay])
async def get_conversations_by_day(
    periodo: str = Query("30d", description="Período: 7d, 30d, 90d"),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    Retorna conversas agrupadas por dia
    """
    start_date = _parse_periodo(periodo)
    
    # Gerar lista de datas
    days = int(periodo[:-1]) if periodo.endswith("d") else 30
    date_list = [
        (datetime.utcnow() - timedelta(days=i)).date()
        for i in range(days - 1, -1, -1)
    ]
    
    result_data = []
    
    for date in date_list:
        date_start = datetime.combine(date, datetime.min.time())
        date_end = datetime.combine(date, datetime.max.time())
        
        # Total de conversas
        result = await db.execute(
            select(func.count(Conversation.id)).where(
                and_(
                    Conversation.tenant_id == tenant_id,
                    Conversation.created_at >= date_start,
                    Conversation.created_at <= date_end
                )
            )
        )
        total = result.scalar() or 0
        
        # Agendadas (conversas com agendamento)
        result = await db.execute(
            select(func.count(func.distinct(Appointment.conversation_id))).where(
                and_(
                    Appointment.tenant_id == tenant_id,
                    Appointment.created_at >= date_start,
                    Appointment.created_at <= date_end,
                    Appointment.status.in_([
                        AppointmentStatus.AGENDADO,
                        AppointmentStatus.CONFIRMADO
                    ])
                )
            )
        )
        agendadas = result.scalar() or 0
        
        # Canceladas
        result = await db.execute(
            select(func.count(Appointment.id)).where(
                and_(
                    Appointment.tenant_id == tenant_id,
                    Appointment.created_at >= date_start,
                    Appointment.created_at <= date_end,
                    Appointment.status == AppointmentStatus.CANCELADO
                )
            )
        )
        canceladas = result.scalar() or 0
        
        # Faltaram
        result = await db.execute(
            select(func.count(Appointment.id)).where(
                and_(
                    Appointment.tenant_id == tenant_id,
                    Appointment.created_at >= date_start,
                    Appointment.created_at <= date_end,
                    Appointment.status == AppointmentStatus.FALTOU
                )
            )
        )
        faltaram = result.scalar() or 0
        
        result_data.append(
            ConversationsByDay(
                data=date.isoformat(),
                total=total,
                agendadas=agendadas,
                canceladas=canceladas,
                faltaram=faltaram
            )
        )
    
    return result_data


@router.get("/top-procedures", response_model=List[TopProcedure])
async def get_top_procedures(
    limit: int = Query(10, description="Número de procedimentos"),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    Retorna procedimentos mais agendados
    """
    result = await db.execute(
        select(
            Procedure.id,
            Procedure.nome,
            func.count(Appointment.id).label("total")
        )
        .join(Appointment, Appointment.procedure_id == Procedure.id)
        .where(Procedure.tenant_id == tenant_id)
        .group_by(Procedure.id, Procedure.nome)
        .order_by(func.count(Appointment.id).desc())
        .limit(limit)
    )
    
    procedures = []
    for row in result:
        procedures.append(
            TopProcedure(
                id=row.id,
                nome=row.nome,
                total_agendamentos=row.total
            )
        )
    
    return procedures


@router.get("/agent-performance", response_model=AgentPerformance)
async def get_agent_performance(
    periodo: str = Query("7d", description="Período: 7d, 30d"),
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    Retorna métricas de performance do agente
    """
    start_date = _parse_periodo(periodo)
    
    # Total de conversas
    result = await db.execute(
        select(func.count(Conversation.id)).where(
            and_(
                Conversation.tenant_id == tenant_id,
                Conversation.created_at >= start_date
            )
        )
    )
    total_conversas = result.scalar() or 0
    
    # Conversas escaladas (agente_ativo = False)
    result = await db.execute(
        select(func.count(Conversation.id)).where(
            and_(
                Conversation.tenant_id == tenant_id,
                Conversation.agente_ativo == False,
                Conversation.created_at >= start_date
            )
        )
    )
    escaladas = result.scalar() or 0
    
    # Taxa de escalação
    taxa_escalacao = (
        (escaladas / total_conversas * 100)
        if total_conversas > 0 else 0
    )
    
    # Conversas com agendamento
    result = await db.execute(
        select(func.count(func.distinct(Appointment.conversation_id))).where(
            and_(
                Appointment.tenant_id == tenant_id,
                Appointment.created_at >= start_date
            )
        )
    )
    com_agendamento = result.scalar() or 0
    
    # Taxa de agendamento
    taxa_agendamento = (
        (com_agendamento / total_conversas * 100)
        if total_conversas > 0 else 0
    )
    
    # Tempo médio de resolução (em minutos)
    result = await db.execute(
        select(
            func.avg(
                func.extract('epoch', Conversation.updated_at - Conversation.created_at) / 60
            )
        ).where(
            and_(
                Conversation.tenant_id == tenant_id,
                Conversation.status == ConversationStatus.CONCLUIDO,
                Conversation.created_at >= start_date
            )
        )
    )
    tempo_medio = result.scalar() or 0
    
    return AgentPerformance(
        taxa_escalacao=round(taxa_escalacao, 2),
        taxa_agendamento=round(taxa_agendamento, 2),
        tempo_medio_resolucao_minutos=round(tempo_medio, 2)
    )
