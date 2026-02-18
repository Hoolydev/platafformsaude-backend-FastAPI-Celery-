"""
Tool: Calendar — buscar horários, criar e cancelar agendamentos
"""

from typing import List, Optional, Dict, Any
from datetime import date, datetime
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.calendar import CalendarConnection, CalendarProvider


async def _get_calendar_connection(db: AsyncSession, tenant_id: int) -> Optional[CalendarConnection]:
    result = await db.execute(
        select(CalendarConnection).where(
            CalendarConnection.tenant_id == tenant_id,
            CalendarConnection.ativo == True,  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


async def buscar_horarios_disponiveis(
    db: AsyncSession,
    tenant_id: int,
    data: date,
    procedimento_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Busca slots livres no calendário do tenant para a data informada.
    Retorna lista de {inicio, fim} em ISO 8601.
    """
    conn = await _get_calendar_connection(db, tenant_id)
    if not conn:
        return []

    creds = conn.credenciais or {}

    if conn.provider == CalendarProvider.google:
        return await _google_buscar_slots(creds, conn.id_agenda, data)

    if conn.provider == CalendarProvider.feegow:
        return await _feegow_buscar_slots(creds, data, procedimento_id)

    return []


async def _google_buscar_slots(
    creds: Dict[str, Any], calendar_id: Optional[str], data: date
) -> List[Dict[str, Any]]:
    """Consulta Google Calendar FreeBusy API."""
    access_token = creds.get("access_token", "")
    cal_id = calendar_id or "primary"
    time_min = f"{data.isoformat()}T00:00:00Z"
    time_max = f"{data.isoformat()}T23:59:59Z"

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            "https://www.googleapis.com/calendar/v3/freeBusy",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "timeMin": time_min,
                "timeMax": time_max,
                "items": [{"id": cal_id}],
            },
        )
        if resp.status_code != 200:
            return []

        busy = resp.json().get("calendars", {}).get(cal_id, {}).get("busy", [])
        # Retorna os períodos ocupados — o front/agente calcula os livres
        return [{"tipo": "ocupado", "inicio": b["start"], "fim": b["end"]} for b in busy]


async def _feegow_buscar_slots(
    creds: Dict[str, Any], data: date, procedimento_id: Optional[int]
) -> List[Dict[str, Any]]:
    """Consulta Feegow API para horários disponíveis."""
    api_key = creds.get("api_key", "")
    base_url = creds.get("base_url", "https://app.feegow.com/v1")

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{base_url}/appointments/available",
            headers={"x-api-key": api_key},
            params={"date": data.isoformat(), "procedure_id": procedimento_id},
        )
        if resp.status_code != 200:
            return []
        return resp.json().get("slots", [])


async def criar_agendamento(
    db: AsyncSession,
    tenant_id: int,
    contact_id: int,
    procedimento_id: int,
    data_hora: datetime,
    titulo: str = "Consulta",
) -> Dict[str, Any]:
    """Cria evento no calendário do tenant."""
    conn = await _get_calendar_connection(db, tenant_id)
    if not conn:
        return {"erro": "Nenhum calendário configurado"}

    creds = conn.credenciais or {}

    if conn.provider == CalendarProvider.google:
        return await _google_criar_evento(creds, conn.id_agenda, data_hora, titulo)

    if conn.provider == CalendarProvider.feegow:
        return await _feegow_criar_agendamento(creds, contact_id, procedimento_id, data_hora)

    return {"erro": f"Provider {conn.provider} não suportado para criação"}


async def _google_criar_evento(
    creds: Dict[str, Any], calendar_id: Optional[str], data_hora: datetime, titulo: str
) -> Dict[str, Any]:
    from datetime import timedelta
    access_token = creds.get("access_token", "")
    cal_id = calendar_id or "primary"
    start = data_hora.isoformat()
    end = (data_hora + timedelta(minutes=30)).isoformat()

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"https://www.googleapis.com/calendar/v3/calendars/{cal_id}/events",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "summary": titulo,
                "start": {"dateTime": start, "timeZone": "America/Sao_Paulo"},
                "end": {"dateTime": end, "timeZone": "America/Sao_Paulo"},
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return {"id_evento": data.get("id"), "link": data.get("htmlLink")}


async def _feegow_criar_agendamento(
    creds: Dict[str, Any], contact_id: int, procedimento_id: int, data_hora: datetime
) -> Dict[str, Any]:
    api_key = creds.get("api_key", "")
    base_url = creds.get("base_url", "https://app.feegow.com/v1")

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{base_url}/appointments",
            headers={"x-api-key": api_key},
            json={
                "patient_id": contact_id,
                "procedure_id": procedimento_id,
                "datetime": data_hora.isoformat(),
            },
        )
        resp.raise_for_status()
        return resp.json()


async def cancelar_agendamento(
    db: AsyncSession,
    tenant_id: int,
    id_evento: str,
) -> Dict[str, Any]:
    """Cancela/deleta evento no calendário do tenant."""
    conn = await _get_calendar_connection(db, tenant_id)
    if not conn:
        return {"erro": "Nenhum calendário configurado"}

    creds = conn.credenciais or {}

    if conn.provider == CalendarProvider.google:
        access_token = creds.get("access_token", "")
        cal_id = conn.id_agenda or "primary"
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.delete(
                f"https://www.googleapis.com/calendar/v3/calendars/{cal_id}/events/{id_evento}",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            return {"cancelado": resp.status_code in (200, 204)}

    if conn.provider == CalendarProvider.feegow:
        api_key = creds.get("api_key", "")
        base_url = creds.get("base_url", "https://app.feegow.com/v1")
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.delete(
                f"{base_url}/appointments/{id_evento}",
                headers={"x-api-key": api_key},
            )
            return {"cancelado": resp.status_code in (200, 204)}

    return {"erro": f"Provider {conn.provider} não suportado para cancelamento"}
