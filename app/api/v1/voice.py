"""
Voice Integration Endpoints - Retell AI
"""

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional
from pydantic import BaseModel

from app.database import get_db
from app.integrations.voice import RetellAIHandler, ElevenLabsSender


router = APIRouter(prefix="/integrations/retell", tags=["Voice Integrations"])


class RetellWebhookPayload(BaseModel):
    """Payload do webhook Retell AI"""
    call_id: str
    transcript: str
    turn: int
    is_final: bool
    customer_phone: Optional[str] = None
    customer_name: Optional[str] = None


class RetellCallEndedPayload(BaseModel):
    """Payload de fim de ligação"""
    call_id: str
    transcript: str
    duration_seconds: int
    customer_phone: Optional[str] = None
    recording_url: Optional[str] = None


@router.post("/webhook/{tenant_id}/{agent_id}")
async def retell_webhook(
    tenant_id: int,
    agent_id: int,
    payload: RetellWebhookPayload,
    db: AsyncSession = Depends(get_db)
):
    """
    Webhook para processar ligações do Retell AI em tempo real
    
    Args:
        tenant_id: ID do tenant
        agent_id: ID do agente
        payload: Dados da ligação
    
    Returns:
        {"response": "texto da resposta"}
    """
    try:
        handler = RetellAIHandler()
        response = await handler.process_webhook(
            tenant_id=tenant_id,
            agent_id=agent_id,
            webhook_data=payload.dict()
        )
        return response
    
    except Exception as e:
        print(f"Erro no webhook Retell: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"response": "Desculpe, ocorreu um erro. Tente novamente."}


@router.post("/call-ended/{tenant_id}")
async def retell_call_ended(
    tenant_id: int,
    payload: RetellCallEndedPayload,
    db: AsyncSession = Depends(get_db)
):
    """
    Webhook para processar fim de ligação
    
    Salva transcrição completa e dispara follow-up
    """
    try:
        handler = RetellAIHandler()
        await handler.process_call_ended(
            tenant_id=tenant_id,
            call_data=payload.dict()
        )
        return {"status": "success"}
    
    except Exception as e:
        print(f"Erro ao processar fim de ligação: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-tts/{tenant_id}")
async def test_tts(
    tenant_id: int,
    text: str,
    voice_id: str = "21m00Tcm4TlvDq8ikWAM",  # Rachel (default)
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint de teste para ElevenLabs TTS
    
    Args:
        tenant_id: ID do tenant
        text: Texto para converter
        voice_id: ID da voz
    
    Returns:
        {"audio_url": "...", "cached": bool}
    """
    try:
        sender = ElevenLabsSender()
        result = await sender.text_to_speech(
            text=text,
            voice_id=voice_id,
            tenant_id=tenant_id
        )
        return result
    
    except Exception as e:
        print(f"Erro ao gerar TTS: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
