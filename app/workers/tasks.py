import os
import httpx
from celery import shared_task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio

from app.database import get_session_factory
from app.models.message import Message, MessageOrigem, MessageTipo
from app.models.conversation import Conversation, ConversationStatus
from app.models.agent import Agent
from app.models.whatsapp_connection import WhatsappConnection


def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@shared_task(name="processar_mensagem")
def processar_mensagem(conversation_id: int, mensagem_cliente: str):
    return run_async(_processar_mensagem(conversation_id, mensagem_cliente))


async def _processar_mensagem(conversation_id: int, mensagem_cliente: str):
    factory = get_session_factory()
    async with factory() as db:
        # Buscar conversa
        result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversa = result.scalar_one_or_none()
        if not conversa:
            return {"erro": "Conversa não encontrada"}

        # Só processar se estiver ativo (agente respondendo)
        if conversa.status != ConversationStatus.ativo:
            return {"info": "Conversa não está ativa para agente"}

        # Buscar agente ativo do tenant
        result = await db.execute(
            select(Agent).where(
                Agent.tenant_id == conversa.tenant_id,
                Agent.ativo == True
            )
        )
        agente = result.scalar_one_or_none()
        if not agente:
            return {"erro": "Nenhum agente ativo encontrado"}

        # Buscar histórico recente (últimas 10 mensagens)
        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.criado_em.desc())
            .limit(10)
        )
        historico = list(reversed(result.scalars().all()))

        # Montar mensagens para o LLM
        messages = []
        for msg in historico:
            role = "user" if msg.origem == MessageOrigem.cliente else "assistant"
            messages.append({"role": role, "content": msg.conteudo})

        # Chamar LLM
        resposta = await chamar_llm(
            modelo=agente.modelo_llm or "gpt-4o-mini",
            instrucoes=agente.instrucoes or "Você é um assistente de clínica médica.",
            messages=messages,
            mensagem_atual=mensagem_cliente,
        )

        if not resposta:
            return {"erro": "LLM não retornou resposta"}

        # Salvar resposta no banco
        nova_msg = Message(
            conversation_id=conversation_id,
            tenant_id=conversa.tenant_id,
            origem=MessageOrigem.agente,
            tipo=MessageTipo.texto,
            conteudo=resposta,
        )
        db.add(nova_msg)
        await db.commit()

        # Enviar via WhatsApp
        result = await db.execute(
            select(WhatsappConnection).where(
                WhatsappConnection.tenant_id == conversa.tenant_id,
                WhatsappConnection.ativo == True
            )
        )
        conexao = result.scalar_one_or_none()
        if conexao:
            await enviar_whatsapp(conexao, conversa.canal_id, resposta)

        return {"ok": True, "resposta": resposta}


async def chamar_llm(modelo: str, instrucoes: str, messages: list, mensagem_atual: str) -> str:
    openai_key = os.environ.get("OPENAI_API_KEY", "")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")

    if "claude" in modelo and anthropic_key:
        return await chamar_anthropic(anthropic_key, modelo, instrucoes, messages, mensagem_atual)
    elif openai_key:
        return await chamar_openai(openai_key, modelo, instrucoes, messages, mensagem_atual)
    else:
        return "Desculpe, estou temporariamente indisponível. Por favor, aguarde um atendente."


async def chamar_openai(api_key: str, modelo: str, instrucoes: str, messages: list, mensagem_atual: str) -> str:
    messages_payload = [{"role": "system", "content": instrucoes}]
    messages_payload.extend(messages)
    messages_payload.append({"role": "user", "content": mensagem_atual})

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            res = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"model": modelo, "messages": messages_payload, "max_tokens": 500},
            )
            res.raise_for_status()
            data = res.json()
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Erro OpenAI: {e}")
        return "Desculpe, tive um problema ao processar sua mensagem com OpenAI."


async def chamar_anthropic(api_key: str, modelo: str, instrucoes: str, messages: list, mensagem_atual: str) -> str:
    messages_payload = list(messages)
    messages_payload.append({"role": "user", "content": mensagem_atual})

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            res = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                },
                json={
                    "model": modelo,
                    "system": instrucoes,
                    "messages": messages_payload,
                    "max_tokens": 500,
                },
            )
            res.raise_for_status()
            data = res.json()
            return data["content"][0]["text"]
    except Exception as e:
        print(f"Erro Anthropic: {e}")
        return "Desculpe, tive um problema ao processar sua mensagem com Anthropic."


async def enviar_whatsapp(conexao, telefone: str, mensagem: str):
    try:
        config = conexao.config or {}
        provider = conexao.provider.value if hasattr(conexao.provider, 'value') else str(conexao.provider)
        
        if provider == "zapi":
            instance_id = config.get("instance_id", "")
            token = config.get("token", "")
            client_token = config.get("token_secreto", "")
            async with httpx.AsyncClient(timeout=15) as client:
                await client.post(
                    f"https://api.z-api.io/instances/{instance_id}/token/{token}/send-text",
                    headers={"Client-Token": client_token},
                    json={"phone": telefone, "message": mensagem},
                )
        elif provider == "evolution":
            api_url = config.get("api_url", "")
            api_key = config.get("api_key", "")
            instance = config.get("instance", "")
            async with httpx.AsyncClient(timeout=15) as client:
                await client.post(
                    f"{api_url}/message/sendText/{instance}",
                    headers={"apikey": api_key},
                    json={"number": telefone, "text": mensagem},
                )
    except Exception as e:
        print(f"Erro ao enviar WhatsApp: {e}")


@shared_task(name="verificar_leads_inativos")
def verificar_leads_inativos():
    return run_async(_verificar_leads_inativos())


async def _verificar_leads_inativos():
    # Placeholder para recuperação de leads
    return {"ok": True, "info": "Verificação de leads executada"}
