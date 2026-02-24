"""
Health & Seed routes
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
