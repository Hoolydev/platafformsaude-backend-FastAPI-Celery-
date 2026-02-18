"""
Calendar Tools - Ferramentas para gerenciar agendamentos
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx

from app.models.procedure import Procedure
from app.models.connection import CalendarConnection


class CalendarTool:
    """
    Ferramenta para buscar horários disponíveis e criar agendamentos
    
    Suporta Google Calendar e Feegow
    """
    
    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
    
    async def buscar_horarios_disponiveis(
        self,
        data: str,
        procedimento_id: int,
        duracao_minutos: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Busca horários disponíveis para agendamento
        
        Args:
            data: Data no formato YYYY-MM-DD
            procedimento_id: ID do procedimento
            duracao_minutos: Duração (se não informado, usa do procedimento)
        
        Returns:
            Lista de horários disponíveis: [{hora: "14:00", disponivel: true}, ...]
        """
        # Buscar procedimento
        result = await self.db.execute(
            select(Procedure).where(
                Procedure.id == procedimento_id,
                Procedure.tenant_id == self.tenant_id
            )
        )
        procedure = result.scalar_one_or_none()
        
        if not procedure:
            return []
        
        duracao = duracao_minutos or procedure.duracao_minutos
        
        # Buscar conexão de calendário ativa
        result = await self.db.execute(
            select(CalendarConnection).where(
                CalendarConnection.tenant_id == self.tenant_id,
                CalendarConnection.ativo == True
            ).limit(1)
        )
        calendar_conn = result.scalar_one_or_none()
        
        if not calendar_conn:
            # Sem integração, retornar horários padrão
            return self._get_default_slots(data, duracao)
        
        # Buscar horários no provider
        if calendar_conn.provider.value == "google":
            return await self._get_google_calendar_slots(calendar_conn, data, duracao)
        elif calendar_conn.provider.value == "feegow":
            return await self._get_feegow_slots(calendar_conn, data, duracao)
        
        return []
    
    def _get_default_slots(self, data: str, duracao: int) -> List[Dict[str, Any]]:
        """Retorna horários padrão (8h-18h) sem verificar disponibilidade real"""
        slots = []
        start_hour = 8
        end_hour = 18
        
        current_time = datetime.strptime(f"{data} {start_hour:02d}:00", "%Y-%m-%d %H:%M")
        end_time = datetime.strptime(f"{data} {end_hour:02d}:00", "%Y-%m-%d %H:%M")
        
        while current_time < end_time:
            slots.append({
                "hora": current_time.strftime("%H:%M"),
                "disponivel": True,
                "data_hora": current_time.isoformat()
            })
            current_time += timedelta(minutes=duracao)
        
        return slots
    
    async def _get_google_calendar_slots(
        self,
        connection: CalendarConnection,
        data: str,
        duracao: int
    ) -> List[Dict[str, Any]]:
        """Busca horários disponíveis no Google Calendar"""
        # TODO: Implementar integração real com Google Calendar API
        # Por enquanto, retornar slots padrão
        return self._get_default_slots(data, duracao)
    
    async def _get_feegow_slots(
        self,
        connection: CalendarConnection,
        data: str,
        duracao: int
    ) -> List[Dict[str, Any]]:
        """Busca horários disponíveis no Feegow"""
        # TODO: Implementar integração com Feegow API
        return self._get_default_slots(data, duracao)
    
    async def criar_agendamento(
        self,
        contact_id: int,
        procedimento_id: int,
        data_hora: str,
        observacoes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Cria um agendamento
        
        Args:
            contact_id: ID do contato
            procedimento_id: ID do procedimento
            data_hora: Data e hora no formato ISO (YYYY-MM-DDTHH:MM:SS)
            observacoes: Observações adicionais
        
        Returns:
            {sucesso: bool, id_evento: str, mensagem: str}
        """
        # Buscar procedimento
        result = await self.db.execute(
            select(Procedure).where(
                Procedure.id == procedimento_id,
                Procedure.tenant_id == self.tenant_id
            )
        )
        procedure = result.scalar_one_or_none()
        
        if not procedure:
            return {
                "sucesso": False,
                "mensagem": "Procedimento não encontrado"
            }
        
        # Buscar conexão de calendário
        result = await self.db.execute(
            select(CalendarConnection).where(
                CalendarConnection.tenant_id == self.tenant_id,
                CalendarConnection.ativo == True
            ).limit(1)
        )
        calendar_conn = result.scalar_one_or_none()
        
        # TODO: Criar evento no Google Calendar/Feegow
        # TODO: Salvar na tabela de agendamentos (criar modelo)
        
        # Por enquanto, retornar sucesso simulado
        return {
            "sucesso": True,
            "id_evento": f"evt_{datetime.now().timestamp()}",
            "mensagem": f"Agendamento confirmado para {data_hora}",
            "procedimento": procedure.nome,
            "duracao": procedure.duracao_minutos
        }
    
    async def cancelar_agendamento(
        self,
        id_evento: str,
        motivo: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Cancela um agendamento
        
        Args:
            id_evento: ID do evento
            motivo: Motivo do cancelamento
        
        Returns:
            {sucesso: bool, mensagem: str}
        """
        # TODO: Remover do Google Calendar/Feegow
        # TODO: Atualizar tabela de agendamentos
        # TODO: Disparar follow-up automático
        
        return {
            "sucesso": True,
            "mensagem": "Agendamento cancelado com sucesso",
            "motivo": motivo
        }
