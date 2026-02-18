"""
User Model - Usuários do sistema
"""

from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class UserRole(str, enum.Enum):
    """Roles de usuário"""
    ADMIN = "admin"
    ATENDENTE = "atendente"
    VISUALIZADOR = "visualizador"


class User(Base):
    """
    Modelo de Usuário
    
    Cada usuário pertence a um tenant e tem um role específico
    """
    __tablename__ = "users"
    
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    nome = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    senha_hash = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.ATENDENTE, nullable=False)
    ativo = Column(Boolean, default=True, nullable=False)
    
    # Avatar e informações adicionais
    avatar_url = Column(String(500), nullable=True)
    telefone = Column(String(20), nullable=True)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    conversations_atendidas = relationship("Conversation", back_populates="atendente", foreign_keys="Conversation.atendente_id")
    
    def __repr__(self):
        return f"<User {self.nome} ({self.email}) - {self.role}>"
    
    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN
    
    @property
    def is_atendente(self) -> bool:
        return self.role in [UserRole.ADMIN, UserRole.ATENDENTE]
