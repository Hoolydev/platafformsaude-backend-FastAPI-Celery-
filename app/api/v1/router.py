"""
API v1 Router — agrega todas as rotas com prefixo /api/v1
"""

from fastapi import APIRouter

from app.api.v1 import auth, tenants, users, contacts, conversations, messages, agents, procedures, whatsapp, webhooks

router = APIRouter(prefix="/api/v1")

router.include_router(auth.router)
router.include_router(tenants.router)
router.include_router(users.router)
router.include_router(contacts.router)
router.include_router(conversations.router)
router.include_router(messages.router)
router.include_router(agents.router)
router.include_router(procedures.router)
router.include_router(whatsapp.router)
router.include_router(webhooks.router)
