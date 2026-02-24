"""
API: Flows
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.flow import Flow, FlowNode, FlowEdge
from app.schemas.flow import FlowCreate, FlowResponse, FlowDetailResponse
from app.auth.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/flows", tags=["Flows"])


@router.post("/", response_model=FlowResponse, status_code=status.HTTP_201_CREATED)
def create_flow(
    flow_in: FlowCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Criar fluxo principal
    db_flow = Flow(
        tenant_id=flow_in.tenant_id,
        nome=flow_in.nome,
        descricao=flow_in.descricao,
        ativo=flow_in.ativo,
        configuracoes=flow_in.configuracoes
    )
    db.add(db_flow)
    db.commit()
    db.refresh(db_flow)

    # Criar nós
    node_map = {} # mapeia IDs temporários (se houver) para IDs reais do DB
    for node_in in flow_in.nodes:
        db_node = FlowNode(
            flow_id=db_flow.id,
            tipo=node_in.tipo,
            nome=node_in.nome,
            posicao=node_in.posicao,
            configuracoes=node_in.configuracoes
        )
        db.add(db_node)
        db.flush() # flush para pegar o ID sem commitar tudo
        if node_in.id is not None:
             node_map[node_in.id] = db_node.id
        else:
             node_map[len(node_map)] = db_node.id # fallback to index

    # Criar arestas
    for edge_in in flow_in.edges:
        # Tenta resolver o target/source se forem IDs temporários do frontend
        source_id = node_map.get(edge_in.source_node_id, edge_in.source_node_id)
        target_id = node_map.get(edge_in.target_node_id, edge_in.target_node_id)

        db_edge = FlowEdge(
            flow_id=db_flow.id,
            source_node_id=source_id,
            target_node_id=target_id,
            condicao=edge_in.condicao,
            configuracoes=edge_in.configuracoes
        )
        db.add(db_edge)

    db.commit()
    return db_flow


@router.get("/", response_model=List[FlowResponse])
def list_flows(
    tenant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(Flow).filter(Flow.tenant_id == tenant_id).all()


@router.get("/{flow_id}", response_model=FlowDetailResponse)
def get_flow(
    flow_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_flow = db.query(Flow).filter(Flow.id == flow_id).first()
    if not db_flow:
        raise HTTPException(status_code=404, detail="Flow not found")
    
    # SQLAlchemy relationships will load nodes and edges
    return db_flow


@router.delete("/{flow_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_flow(
    flow_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_flow = db.query(Flow).filter(Flow.id == flow_id).first()
    if not db_flow:
        raise HTTPException(status_code=404, detail="Flow not found")
    
    db.delete(db_flow)
    db.commit()
    return None
