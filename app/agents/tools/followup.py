"""
Tool: Follow-up — agendar envio futuro via Celery
"""

from datetime import datetime
from typing import Optional


async def agendar_followup(
    tenant_id: int,
    contact_id: int,
    mensagem: str,
    data_hora: datetime,
    conversation_id: Optional[int] = None,
) -> dict:
    """
    Agenda envio de follow-up via Celery (eta).
    Importa a task de forma lazy para evitar circular imports.
    """
    try:
        from app.workers.tasks import send_followup_message  # noqa: F401 — importado lazy

        result = send_followup_message.apply_async(
            kwargs={
                "tenant_id": tenant_id,
                "contact_id": contact_id,
                "conversation_id": conversation_id,
                "mensagem": mensagem,
            },
            eta=data_hora,
        )
        return {
            "agendado": True,
            "task_id": result.id,
            "data_hora": data_hora.isoformat(),
        }
    except Exception as e:
        return {"agendado": False, "erro": str(e)}
