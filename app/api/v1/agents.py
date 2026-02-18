"""
Agents Endpoints - CRUD de agentes IA
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List
from app.database import get_db
from app.models.user import User, UserRole
from app.models.agent import Agent, AgentTool
from app.schemas.agent import AgentCreate, AgentUpdate, AgentResponse, AgentToolCreate
from app.auth.dependencies import get_current_active_user, require_role
from app.middleware.tenant import get_tenant_id

router = APIRouter()


@router.get("/", response_model=List[AgentResponse], summary="Listar agentes")
async def list_agents(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Lista todos os agentes do tenant"""
    tenant_id = get_tenant_id(request) or current_user.tenant_id
    
    result = await db.execute(
        select(Agent)
        .options(selectinload(Agent.tools))
        .where(Agent.tenant_id == tenant_id)
        .offset(skip)
        .limit(limit)
    )
    agents = result.scalars().all()
    return agents


@router.post("/", response_model=AgentResponse, status_code=status.HTTP_201_CREATED, summary="Criar agente")
async def create_agent(
    request: Request,
    agent_data: AgentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """Cria um novo agente IA (apenas admins)"""
    tenant_id = get_tenant_id(request) or current_user.tenant_id
    
    # Criar agente
    agent = Agent(
        tenant_id=tenant_id,
        nome=agent_data.nome,
        instrucoes=agent_data.instrucoes,
        modelo_llm=agent_data.modelo_llm,
        temperatura=agent_data.temperatura,
        max_tokens=agent_data.max_tokens,
        voz_elevenlabs=agent_data.voz_elevenlabs,
        usar_voz=agent_data.usar_voz,
        configuracoes=agent_data.configuracoes
    )
    
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    
    return agent


@router.get("/{agent_id}", response_model=AgentResponse, summary="Obter agente")
async def get_agent(
    agent_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Obtém um agente específico"""
    tenant_id = get_tenant_id(request) or current_user.tenant_id
    
    result = await db.execute(
        select(Agent)
        .options(selectinload(Agent.tools))
        .where(
            Agent.id == agent_id,
            Agent.tenant_id == tenant_id
        )
    )
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agente não encontrado"
        )
    
    return agent


@router.patch("/{agent_id}", response_model=AgentResponse, summary="Atualizar agente")
async def update_agent(
    agent_id: int,
    agent_data: AgentUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """Atualiza um agente (apenas admins)"""
    tenant_id = get_tenant_id(request) or current_user.tenant_id
    
    result = await db.execute(
        select(Agent).where(
            Agent.id == agent_id,
            Agent.tenant_id == tenant_id
        )
    )
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agente não encontrado"
        )
    
    # Atualizar campos
    update_data = agent_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(agent, field, value)
    
    await db.commit()
    await db.refresh(agent)
    
    return agent


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Deletar agente")
async def delete_agent(
    agent_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """Deleta um agente (apenas admins)"""
    tenant_id = get_tenant_id(request) or current_user.tenant_id
    
    result = await db.execute(
        select(Agent).where(
            Agent.id == agent_id,
            Agent.tenant_id == tenant_id
        )
    )
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agente não encontrado"
        )
    
    await db.delete(agent)
    await db.commit()
    
    return None


@router.post("/{agent_id}/tools", status_code=status.HTTP_201_CREATED, summary="Adicionar ferramenta ao agente")
async def add_agent_tool(
    agent_id: int,
    tool_data: AgentToolCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """Adiciona uma ferramenta a um agente"""
    tenant_id = get_tenant_id(request) or current_user.tenant_id
    
    # Verificar se agente existe
    result = await db.execute(
        select(Agent).where(
            Agent.id == agent_id,
            Agent.tenant_id == tenant_id
        )
    )
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agente não encontrado"
        )
    
    # Criar ferramenta
    tool = AgentTool(
        agent_id=agent_id,
        tipo=tool_data.tipo,
        ativo=tool_data.ativo,
        configuracoes=tool_data.configuracoes
    )
    
    db.add(tool)
    await db.commit()
    await db.refresh(tool)
    
    return tool
