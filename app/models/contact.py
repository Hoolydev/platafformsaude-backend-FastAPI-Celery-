"""
Model: Contact
"""

from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from app.database import Base


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    telefone = Column(String(30), nullable=False, index=True)
    nome = Column(String(255))
    email = Column(String(255))
    tags = Column(JSONB, default=[])
    metadados = Column(JSONB, default={})
