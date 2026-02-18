"""
Procedure Model - Procedimentos/Serviços
"""

from sqlalchemy import Column, String, Text, Integer, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base


class Procedure(Base):
    """
    Modelo de Procedimento/Serviço
    
    Representa os procedimentos médicos/serviços oferecidos pela clínica
    """
    __tablename__ = "procedures"
    
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    
    nome = Column(String(255), nullable=False)
    descricao = Column(Text, nullable=True)
    
    # Duração e valor
    duracao_minutos = Column(Integer, nullable=False, default=30)
    valor = Column(Float, nullable=True)  # Pode ser null se não divulgar preço
    
    # Convênios aceitos
    convenios_aceitos = Column(JSON, default=list, nullable=False)
    
    # Categoria e tags
    categoria = Column(String(100), nullable=True)
    tags = Column(JSON, default=list, nullable=False)
    
    # Disponibilidade
    ativo = Column(Boolean, default=True, nullable=False)
    
    # Relacionamentos ORM
    tenant = relationship("Tenant", back_populates="procedures")
    appointments = relationship("Appointment", back_populates="procedure", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Procedure {self.nome} - {self.duracao_minutos}min>"
