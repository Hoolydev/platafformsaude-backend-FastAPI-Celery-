"""
API v1 package
"""

from fastapi import APIRouter
from app.api.v1 import auth, users, contacts, conversations, agents, procedures, webhooks, websocket

api_router = APIRouter()

# Incluir routers
api_router.include_router(auth.router, prefix="/auth", tags=["Autenticação"])
api_router.include_router(users.router, prefix="/users", tags=["Usuários"])
api_router.include_router(contacts.router, prefix="/contacts", tags=["Contatos"])
api_router.include_router(conversations.router, prefix="/conversations", tags=["Conversas"])
api_router.include_router(agents.router, prefix="/agents", tags=["Agentes IA"])
api_router.include_router(procedures.router, prefix="/procedures", tags=["Procedimentos"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])

__all__ = ["api_router"]
