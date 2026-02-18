"""
Contact Model - Contatos/Clientes
"""

from sqlalchemy import Column, String, Integer, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from app.database import Base


class Contact(Base):
    """
    Modelo de Contato (Cliente/Paciente)
    
    Armazena informações dos clientes que interagem via WhatsApp
    """
    __tablename__ = "contacts"
    
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    telefone = Column(String(20), nullable=False, index=True)
    nome = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    
    # Metadados flexíveis (CPF, data nascimento, endereço, etc)
    metadados = Column(JSON, default=dict, nullable=False)
    
    # Tags e segmentação
    tags = Column(JSON, default=list, nullable=False)
    
    # Relacionamentos ORM
    tenant = relationship("Tenant", back_populates="contacts")
    conversations = relationship("Conversation", back_populates="contact", cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="contact", cascade="all, delete-orphan")
    lead_recoveries = relationship("LeadRecovery", back_populates="contact", cascade="all, delete-orphan")
    
    # Índice composto para garantir telefone único por tenant
    __table_args__ = (
        Index('idx_tenant_telefone', 'tenant_id', 'telefone', unique=True),
    )
    
    def __repr__(self):
        return f"<Contact {self.nome or 'Sem nome'} ({self.telefone})>"
