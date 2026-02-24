"""
Health, Seed & Debug routes
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import bcrypt

from app.database import get_db
from app.models.user import User
from app.models.tenant import Tenant

router = APIRouter(tags=["health"])


@router.post("/api/v1/seed-admin/")
async def seed_admin(db: AsyncSession = Depends(get_db)):
    """
    Cria o tenant demo e o usuário admin se não existirem.
    Se existirem, reseta a senha para admin123.
    """
    # Verificar/criar tenant
    result = await db.execute(select(Tenant).where(Tenant.subdominio == "demo"))
    tenant = result.scalar_one_or_none()
    if not tenant:
        tenant = Tenant(
            nome="Demo Clinic",
            subdominio="demo",
            ativo=True,
        )
        db.add(tenant)
        await db.flush()

    # Verificar/criar user
    result = await db.execute(select(User).where(User.email == "admin@demo.com"))
    user = result.scalar_one_or_none()

    senha_hash = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode()

    if not user:
        user = User(
            tenant_id=tenant.id,
            email="admin@demo.com",
            nome="Admin Demo",
            senha_hash=senha_hash,
            role="admin",
            ativo=True,
        )
        db.add(user)
        await db.commit()
        return {"message": "Admin criado com sucesso", "email": "admin@demo.com", "senha": "admin123"}
    else:
        user.senha_hash = senha_hash
        user.ativo = True
        await db.commit()
        return {"message": "Senha do admin resetada", "email": "admin@demo.com", "senha": "admin123"}


@router.post("/api/v1/test-agent/")
async def test_agent(db: AsyncSession = Depends(get_db)):
    """
    Testa o pipeline do agente: busca conversa ativa,
    dispara Celery task e retorna resultado.
    """
    from app.models.conversation import Conversation, ConversationStatus
    from app.models.agent import Agent

    info = {}

    # 1. Verificar tenant
    result = await db.execute(select(Tenant).where(Tenant.subdominio == "demo"))
    tenant = result.scalar_one_or_none()
    if not tenant:
        return {"erro": "Tenant demo não encontrado"}
    info["tenant_id"] = tenant.id

    # 2. Verificar agente ativo
    result = await db.execute(
        select(Agent).where(Agent.tenant_id == tenant.id, Agent.ativo == True)
    )
    agente = result.scalar_one_or_none()
    info["agente_ativo"] = agente.nome if agente else None
    info["modelo_llm"] = agente.modelo_llm if agente else None

    # 3. Verificar conversas ativas
    result = await db.execute(
        select(Conversation).where(
            Conversation.tenant_id == tenant.id,
            Conversation.status == ConversationStatus.ativo,
        )
    )
    conversas = result.scalars().all()
    info["conversas_ativas"] = len(conversas)

    # 4. Tentar disparar Celery task na primeira conversa ativa
    if conversas and agente:
        conv = conversas[0]
        info["testando_conversa_id"] = conv.id
        try:
            from app.workers.tasks import processar_mensagem
            task = processar_mensagem.delay(conv.id, "teste automático")
            info["celery_task_id"] = task.id
            info["celery_status"] = "disparado com sucesso"
        except Exception as e:
            info["celery_erro"] = str(e)
    else:
        info["celery_status"] = "sem conversa ou agente para testar"

    # 5. Verificar OPENAI_API_KEY
    import os
    openai_key = os.environ.get("OPENAI_API_KEY", "")
    info["openai_key_configurada"] = bool(openai_key and openai_key != "your-openai-api-key")

    # 6. Verificar Redis/Celery
    try:
        from app.workers.celery_app import celery_app
        inspect = celery_app.control.inspect()
        active = inspect.active()
        info["celery_workers"] = list(active.keys()) if active else []
    except Exception as e:
        info["celery_workers_erro"] = str(e)

    return info
