"""
Model: Procedure
"""

from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from app.database import Base


class Procedure(Base):
    __tablename__ = "procedures"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    nome = Column(String(255), nullable=False)
    duracao_minutos = Column(Integer)
    valor = Column(Numeric(10, 2))
    convenios_aceitos = Column(JSONB, default=[])
    descricao = Column(Text)
