"""
Models for Chatbot Flows
"""

import enum
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, Enum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.database import Base


class Flow(Base):
    __tablename__ = "flows"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    nome = Column(String(255), nullable=False)
    descricao = Column(Text)
    ativo = Column(Boolean, default=True, nullable=False)
    configuracoes = Column(JSONB, default={})

    nodes = relationship("FlowNode", back_populates="flow", cascade="all, delete-orphan")


class FlowNode(Base):
    __tablename__ = "flow_nodes"

    id = Column(Integer, primary_key=True, index=True)
    flow_id = Column(Integer, ForeignKey("flows.id"), nullable=False, index=True)
    tipo = Column(String(50), nullable=False)  # ia, message, question, menu, action, etc.
    nome = Column(String(100))
    posicao = Column(JSONB, default={"x": 0, "y": 0})
    configuracoes = Column(JSONB, default={})

    flow = relationship("Flow", back_populates="nodes")
    source_edges = relationship("FlowEdge", foreign_keys="FlowEdge.source_node_id", back_populates="source_node", cascade="all, delete-orphan")
    target_edges = relationship("FlowEdge", foreign_keys="FlowEdge.target_node_id", back_populates="target_node", cascade="all, delete-orphan")


class FlowEdge(Base):
    __tablename__ = "flow_edges"

    id = Column(Integer, primary_key=True, index=True)
    flow_id = Column(Integer, ForeignKey("flows.id"), nullable=False, index=True)
    source_node_id = Column(Integer, ForeignKey("flow_nodes.id"), nullable=False)
    target_node_id = Column(Integer, ForeignKey("flow_nodes.id"), nullable=False)
    condicao = Column(String(255))
    configuracoes = Column(JSONB, default={})

    source_node = relationship("FlowNode", foreign_keys=[source_node_id], back_populates="source_edges")
    target_node = relationship("FlowNode", foreign_keys=[target_node_id], back_populates="target_edges")
