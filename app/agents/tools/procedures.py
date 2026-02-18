"""
Tool: Procedures — buscar procedimentos do tenant
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.models.procedure import Procedure


async def buscar_procedimento(
    db: AsyncSession,
    tenant_id: int,
    nome: str,
) -> Optional[Dict[str, Any]]:
    """
    Busca um procedimento pelo nome (busca parcial, case-insensitive).
    Retorna o primeiro resultado ou None.
    """
    result = await db.execute(
        select(Procedure).where(
            Procedure.tenant_id == tenant_id,
            Procedure.nome.ilike(f"%{nome}%"),
        )
    )
    proc = result.scalars().first()
    if not proc:
        return None
    return {
        "id": proc.id,
        "nome": proc.nome,
        "duracao_minutos": proc.duracao_minutos,
        "valor": float(proc.valor) if proc.valor else None,
        "convenios_aceitos": proc.convenios_aceitos or [],
        "descricao": proc.descricao,
    }


async def listar_procedimentos(
    db: AsyncSession,
    tenant_id: int,
) -> List[Dict[str, Any]]:
    """Lista todos os procedimentos do tenant."""
    result = await db.execute(
        select(Procedure).where(Procedure.tenant_id == tenant_id).order_by(Procedure.nome)
    )
    procs = result.scalars().all()
    return [
        {
            "id": p.id,
            "nome": p.nome,
            "duracao_minutos": p.duracao_minutos,
            "valor": float(p.valor) if p.valor else None,
            "convenios_aceitos": p.convenios_aceitos or [],
            "descricao": p.descricao,
        }
        for p in procs
    ]
