"""
WhatsApp Webhooks - Recebimento de mensagens de diferentes providers
"""

from fastapi import APIRouter, Request, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any
import hmac
import hashlib
import json
import redis.asyncio as redis
import os

from app.database import get_db
from app.models.connection import WhatsappConnection
from app.services.whatsapp.parsers import parse_webhook_message

router = APIRouter()

# Redis client para fila de mensagens
redis_client = redis.from_url(
    os.getenv("REDIS_URL", "redis://:RedisSecurePass2024!@redis:6379/0"),
    decode_responses=True
)


async def get_whatsapp_connection(
    tenant_id: int,
    connection_id: int,
    db: AsyncSession
) -> WhatsappConnection:
    """Busca conexão WhatsApp"""
    result = await db.execute(
        select(WhatsappConnection).where(
            WhatsappConnection.id == connection_id,
            WhatsappConnection.tenant_id == tenant_id,
            WhatsappConnection.ativo == True
        )
    )
    connection = result.scalar_one_or_none()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conexão WhatsApp não encontrada ou inativa"
        )
    
    return connection


def verify_zapi_signature(payload: bytes, signature: str, token: str) -> bool:
    """Verifica assinatura do webhook Z-API"""
    if not signature:
        return False
    
    expected_signature = hmac.new(
        token.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)


def verify_meta_signature(payload: bytes, signature: str, app_secret: str) -> bool:
    """Verifica assinatura do webhook Meta"""
    if not signature or not signature.startswith("sha256="):
        return False
    
    expected_signature = "sha256=" + hmac.new(
        app_secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)


@router.post("/zapi/{tenant_id}/{connection_id}", summary="Webhook Z-API")
async def zapi_webhook(
    tenant_id: int,
    connection_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Recebe webhooks da Z-API
    
    Valida assinatura, normaliza mensagem e publica na fila Redis
    """
    # Buscar conexão
    connection = await get_whatsapp_connection(tenant_id, connection_id, db)
    
    # Ler payload
    body = await request.body()
    payload = await request.json()
    
    # Validar assinatura (opcional, dependendo da configuração)
    signature = request.headers.get("X-Webhook-Signature")
    if signature:
        token = connection.credenciais.get("webhook_token", "")
        if not verify_zapi_signature(body, signature, token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Assinatura inválida"
            )
    
    # Ignorar mensagens enviadas (apenas receber)
    if payload.get("isGroupMsg") or payload.get("fromMe"):
        return {"status": "ignored"}
    
    try:
        # Normalizar mensagem
        normalized = parse_webhook_message("zapi", payload)
        
        # Adicionar metadados
        message_data = normalized.to_dict()
        message_data["tenant_id"] = tenant_id
        message_data["connection_id"] = connection_id
        message_data["provider"] = "zapi"
        
        # Publicar na fila Redis
        queue_key = f"queue:messages:{tenant_id}"
        await redis_client.lpush(queue_key, json.dumps(message_data))
        
        # Trigger worker (via Celery)
        from app.workers import process_incoming_message
        process_incoming_message.delay(tenant_id, message_data)
        
        return {"status": "received"}
    
    except Exception as e:
        print(f"Erro ao processar webhook Z-API: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erro ao processar mensagem: {str(e)}"
        )


@router.post("/uazapi/{tenant_id}/{connection_id}", summary="Webhook UazAPI")
async def uazapi_webhook(
    tenant_id: int,
    connection_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Recebe webhooks da UazAPI
    """
    # Buscar conexão
    connection = await get_whatsapp_connection(tenant_id, connection_id, db)
    
    # Ler payload
    body = await request.body()
    payload = await request.json()
    
    # Validar token (UazAPI usa token no header)
    auth_token = request.headers.get("Authorization")
    expected_token = connection.credenciais.get("webhook_token")
    if expected_token and auth_token != f"Bearer {expected_token}":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido"
        )
    
    # Ignorar mensagens enviadas
    if payload.get("fromMe"):
        return {"status": "ignored"}
    
    try:
        # Normalizar mensagem
        normalized = parse_webhook_message("uazapi", payload)
        
        # Adicionar metadados
        message_data = normalized.to_dict()
        message_data["tenant_id"] = tenant_id
        message_data["connection_id"] = connection_id
        message_data["provider"] = "uazapi"
        
        # Publicar na fila Redis
        queue_key = f"queue:messages:{tenant_id}"
        await redis_client.lpush(queue_key, json.dumps(message_data))
        
        # Trigger worker
        from app.workers import process_incoming_message
        process_incoming_message.delay(tenant_id, message_data)
        
        return {"status": "received"}
    
    except Exception as e:
        print(f"Erro ao processar webhook UazAPI: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erro ao processar mensagem: {str(e)}"
        )


@router.post("/oficial/{tenant_id}/{connection_id}", summary="Webhook WhatsApp Business API")
async def oficial_webhook(
    tenant_id: int,
    connection_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Recebe webhooks da WhatsApp Business API Oficial (Meta)
    """
    # Buscar conexão
    connection = await get_whatsapp_connection(tenant_id, connection_id, db)
    
    # Ler payload
    body = await request.body()
    payload = await request.json()
    
    # Validar assinatura Meta
    signature = request.headers.get("X-Hub-Signature-256")
    app_secret = connection.credenciais.get("app_secret", "")
    if signature and not verify_meta_signature(body, signature, app_secret):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Assinatura inválida"
        )
    
    # Verificar se é mensagem (não status update)
    try:
        entry = payload["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]
        
        # Ignorar status updates
        if "statuses" in value:
            return {"status": "ignored"}
        
        # Processar apenas mensagens
        if "messages" not in value:
            return {"status": "ignored"}
        
    except (KeyError, IndexError):
        return {"status": "ignored"}
    
    try:
        # Normalizar mensagem
        normalized = parse_webhook_message("oficial", payload)
        
        # Adicionar metadados
        message_data = normalized.to_dict()
        message_data["tenant_id"] = tenant_id
        message_data["connection_id"] = connection_id
        message_data["provider"] = "oficial"
        
        # Publicar na fila Redis
        queue_key = f"queue:messages:{tenant_id}"
        await redis_client.lpush(queue_key, json.dumps(message_data))
        
        # Trigger worker
        from app.workers import process_incoming_message
        process_incoming_message.delay(tenant_id, message_data)
        
        return {"status": "received"}
    
    except Exception as e:
        print(f"Erro ao processar webhook Meta: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erro ao processar mensagem: {str(e)}"
        )


@router.get("/oficial/{tenant_id}/{connection_id}", summary="Verificação webhook Meta")
async def verify_oficial_webhook(
    tenant_id: int,
    connection_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint de verificação para WhatsApp Business API
    
    Meta envia GET request para verificar o webhook
    """
    # Buscar conexão
    connection = await get_whatsapp_connection(tenant_id, connection_id, db)
    
    # Parâmetros de verificação
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    
    # Token de verificação configurado
    verify_token = connection.credenciais.get("verify_token", "")
    
    # Verificar
    if mode == "subscribe" and token == verify_token:
        return int(challenge)
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Verificação falhou"
    )
