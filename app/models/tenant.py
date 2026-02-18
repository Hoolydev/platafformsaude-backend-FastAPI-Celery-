"""
Tenant Model - Multi-tenancy
"""

from sqlalchemy import Column, String, Boolean, JSON
from sqlalchemy.orm import relationship
from app.database import Base


class Tenant(Base):
    """
    Modelo de Tenant (Inquilino) para multi-tenancy
    
    Cada tenant representa uma clínica/empresa que usa a plataforma
    """
    __tablename__ = "tenants"
    
    nome = Column(String(255), nullable=False)
    subdominio = Column(String(100), unique=True, nullable=False, index=True)
    ativo = Column(Boolean, default=True, nullable=False)
    configuracoes = Column(JSON, default=dict, nullable=False)
    
    # Plano e limites
    plano = Column(String(50), default="trial", nullable=False)  # trial, basic, pro, enterprise
    limite_usuarios = Column(Integer, default=5)
    limite_agentes = Column(Integer, default=2)
    limite_conversas_mes = Column(Integer, default=1000)
    
    # Relacionamentos
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    contacts = relationship("Contact", back_populates="tenant", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="tenant", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="tenant", cascade="all, delete-orphan")
    agents = relationship("Agent", back_populates="tenant", cascade="all, delete-orphan")
    procedures = relationship("Procedure", back_populates="tenant", cascade="all, delete-orphan")
    whatsapp_connections = relationship("WhatsappConnection", back_populates="tenant", cascade="all, delete-orphan")
    calendar_connections = relationship("CalendarConnection", back_populates="tenant", cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="tenant", cascade="all, delete-orphan")
    lead_recoveries = relationship("LeadRecovery", back_populates="tenant", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Tenant {self.nome} ({self.subdominio})>"
