"""
Tenant Middleware - Multi-tenancy
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.tenant import Tenant
from typing import Optional
import re


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Middleware para detectar e injetar tenant_id nas requests
    
    Detecta tenant a partir de:
    1. Header X-Tenant-ID (prioridade)
    2. Subdomínio (ex: clinica1.saudeplataform.com)
    3. Query parameter ?tenant_id=X (apenas para desenvolvimento)
    """
    
    async def dispatch(self, request: Request, call_next):
        """
        Processa a request e injeta tenant_id
        """
        tenant_id = None
        tenant = None
        
        # 1. Tentar obter do header
        tenant_id_header = request.headers.get("X-Tenant-ID")
        if tenant_id_header:
            try:
                tenant_id = int(tenant_id_header)
            except ValueError:
                pass
        
        # 2. Tentar obter do subdomínio
        if not tenant_id:
            host = request.headers.get("host", "")
            subdomain = self._extract_subdomain(host)
            
            if subdomain:
                # Buscar tenant pelo subdomínio
                async with AsyncSessionLocal() as db:
                    result = await db.execute(
                        select(Tenant).where(Tenant.subdominio == subdomain)
                    )
                    tenant = result.scalar_one_or_none()
                    if tenant:
                        tenant_id = tenant.id
        
        # 3. Tentar obter do query parameter (apenas desenvolvimento)
        if not tenant_id and request.query_params.get("tenant_id"):
            try:
                tenant_id = int(request.query_params.get("tenant_id"))
            except ValueError:
                pass
        
        # Injetar tenant_id no state da request
        request.state.tenant_id = tenant_id
        request.state.tenant = tenant
        
        # Continuar processamento
        response = await call_next(request)
        
        # Adicionar header de tenant na response (útil para debugging)
        if tenant_id:
            response.headers["X-Tenant-ID"] = str(tenant_id)
        
        return response
    
    def _extract_subdomain(self, host: str) -> Optional[str]:
        """
        Extrai subdomínio do host
        
        Exemplos:
            clinica1.saudeplataform.com -> clinica1
            localhost -> None
            api.saudeplataform.com -> api
        
        Args:
            host: Host da request
        
        Returns:
            Subdomínio ou None
        """
        # Remover porta se presente
        host = host.split(":")[0]
        
        # Ignorar localhost e IPs
        if host in ["localhost", "127.0.0.1"] or re.match(r"^\d+\.\d+\.\d+\.\d+$", host):
            return None
        
        # Dividir por pontos
        parts = host.split(".")
        
        # Se tiver mais de 2 partes, o primeiro é o subdomínio
        # Ex: clinica1.saudeplataform.com -> ["clinica1", "saudeplataform", "com"]
        if len(parts) > 2:
            return parts[0]
        
        return None


def get_tenant_id(request: Request) -> Optional[int]:
    """
    Helper para obter tenant_id da request
    
    Usage:
        @app.get("/items")
        async def get_items(request: Request):
            tenant_id = get_tenant_id(request)
            ...
    
    Args:
        request: FastAPI Request object
    
    Returns:
        tenant_id ou None
    """
    return getattr(request.state, "tenant_id", None)


def get_tenant(request: Request) -> Optional[Tenant]:
    """
    Helper para obter tenant da request
    
    Args:
        request: FastAPI Request object
    
    Returns:
        Tenant object ou None
    """
    return getattr(request.state, "tenant", None)
