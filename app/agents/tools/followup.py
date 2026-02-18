"""
Follow-up Tools - Ferramentas para agendar follow-ups automáticos
"""

from typing import Dict, Any
from datetime import datetime
from app.workers import celery_app


class FollowUpTool:
    """Ferramenta para agendar follow-ups automáticos"""
    
    def __init__(self, tenant_id: int):
        self.tenant_id = tenant_id
    
    async def follow_up_agendar(
        self,
        contato_id: int,
        mensagem: str,
        data_hora: str
    ) -> Dict[str, Any]:
        """
        Agenda follow-up automático
        
        Args:
            contato_id: ID do contato
            mensagem: Mensagem a enviar
            data_hora: Data e hora no formato ISO
        
        Returns:
            {sucesso: bool, task_id: str, mensagem: str}
        """
        # Converter data_hora para datetime
        try:
            scheduled_time = datetime.fromisoformat(data_hora)
        except ValueError:
            return {
                "sucesso": False,
                "mensagem": "Formato de data/hora inválido. Use ISO format (YYYY-MM-DDTHH:MM:SS)"
            }
        
        # Agendar task no Celery
        from app.workers import send_follow_up_message
        
        task = send_follow_up_message.apply_async(
            args=[self.tenant_id, contato_id, mensagem],
            eta=scheduled_time
        )
        
        return {
            "sucesso": True,
            "task_id": task.id,
            "mensagem": f"Follow-up agendado para {data_hora}",
            "scheduled_time": scheduled_time.isoformat()
        }


# Adicionar task ao workers.py
"""
@celery_app.task(name="app.workers.send_follow_up_message")
def send_follow_up_message(tenant_id: int, contact_id: int, message: str):
    '''Envia mensagem de follow-up agendada'''
    return run_async(_send_follow_up_message(tenant_id, contact_id, message))

async def _send_follow_up_message(tenant_id: int, contact_id: int, message: str):
    '''Implementação assíncrona de envio de follow-up'''
    async with AsyncSessionLocal() as db:
        # Buscar contato
        result = await db.execute(
            select(Contact).where(Contact.id == contact_id)
        )
        contact = result.scalar_one_or_none()
        
        if not contact:
            return
        
        # Buscar conexão WhatsApp ativa do tenant
        result = await db.execute(
            select(WhatsappConnection).where(
                WhatsappConnection.tenant_id == tenant_id,
                WhatsappConnection.ativo == True
            ).limit(1)
        )
        connection = result.scalar_one_or_none()
        
        if not connection:
            return
        
        # Enviar mensagem
        from app.services.whatsapp.sender import WhatsAppSender
        sender = WhatsAppSender(connection)
        await sender.send(contact.telefone, "text", message=message)
"""
