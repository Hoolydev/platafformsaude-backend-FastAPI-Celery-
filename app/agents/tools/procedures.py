"""
Procedures Tools - Ferramentas para buscar informações de procedimentos
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.models.procedure import Procedure


class ProceduresTool:
    """Ferramenta para buscar informações sobre procedimentos"""
    
    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
    
    async def buscar_informacoes_procedimento(
        self,
        nome_procedimento: str
    ) -> Optional[Dict[str, Any]]:
        """
        Busca informações de um procedimento pelo nome
        
        Args:
            nome_procedimento: Nome ou parte do nome do procedimento
        
        Returns:
            Dicionário com informações do procedimento ou None
        """
        # Buscar procedimento (case-insensitive, partial match)
        result = await self.db.execute(
            select(Procedure).where(
                Procedure.tenant_id == self.tenant_id,
                Procedure.ativo == True,
                or_(
                    Procedure.nome.ilike(f"%{nome_procedimento}%"),
                    Procedure.categoria.ilike(f"%{nome_procedimento}%")
                )
            ).limit(1)
        )
        procedure = result.scalar_one_or_none()
        
        if not procedure:
            return None
        
        return {
            "id": procedure.id,
            "nome": procedure.nome,
            "descricao": procedure.descricao,
            "duracao_minutos": procedure.duracao_minutos,
            "valor": procedure.valor,
            "convenios_aceitos": procedure.convenios_aceitos,
            "categoria": procedure.categoria,
            "tags": procedure.tags
        }
    
    async def listar_procedimentos(
        self,
        categoria: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Lista todos os procedimentos disponíveis
        
        Args:
            categoria: Filtrar por categoria (opcional)
        
        Returns:
            Lista de procedimentos
        """
        query = select(Procedure).where(
            Procedure.tenant_id == self.tenant_id,
            Procedure.ativo == True
        )
        
        if categoria:
            query = query.where(Procedure.categoria.ilike(f"%{categoria}%"))
        
        result = await self.db.execute(query)
        procedures = result.scalars().all()
        
        return [
            {
                "id": p.id,
                "nome": p.nome,
                "duracao_minutos": p.duracao_minutos,
                "valor": p.valor,
                "categoria": p.categoria
            }
            for p in procedures
        ]
