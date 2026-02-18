"""
Escalation Tools - Ferramentas para escalar conversa para humano
"""

from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.conversation import Conversation, ConversationStatus


class EscalationTool:
    """Ferramenta para escalar conversa para atendente humano"""
    
    def __init__(self, db: AsyncSession, conversation_id: int):
        self.db = db
        self.conversation_id = conversation_id
    
    async def escalar_para_humano(
        self,
        motivo: str,
        urgencia: str = "normal"
    ) -> Dict[str, Any]:
        """
        Escala conversa para atendente humano
        
        Args:
            motivo: Motivo da escalação
            urgencia: "baixa", "normal", "alta"
        
        Returns:
            {sucesso: bool, mensagem: str}
        """
        # Buscar conversa
        result = await self.db.execute(
            select(Conversation).where(Conversation.id == self.conversation_id)
        )
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            return {
                "sucesso": False,
                "mensagem": "Conversa não encontrada"
            }
        
        # Atualizar status
        conversation.agente_ativo = False
        conversation.status = ConversationStatus.ASSUMIDO
        
        # Adicionar motivo nos metadados (se existir campo)
        # TODO: Adicionar campo metadados no modelo Conversation
        
        await self.db.commit()
        
        # Notificar atendentes via WebSocket
        from app.api.v1.websocket import broadcast_to_tenant
        await broadcast_to_tenant(conversation.tenant_id, {
            "event": "agente_escalou",
            "conversation_id": self.conversation_id,
            "motivo": motivo,
            "urgencia": urgencia
        })
        
        return {
            "sucesso": True,
            "mensagem": "Conversa escalada para atendente humano",
            "motivo": motivo,
            "urgencia": urgencia
        }
