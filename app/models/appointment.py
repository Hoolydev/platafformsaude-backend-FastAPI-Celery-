"""
Appointment Model - Agendamentos de consultas
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.database import Base


class AppointmentStatus(enum.Enum):
    """Status do agendamento"""
    AGENDADO = "agendado"
    CONFIRMADO = "confirmado"
    CANCELADO = "cancelado"
    REALIZADO = "realizado"
    FALTOU = "faltou"


class Appointment(Base):
    """
    Agendamentos de consultas/procedimentos
    
    Relaciona Contact + Procedure com data/hora específica
    """
    __tablename__ = "appointments"
    
    # Relacionamentos
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=False, index=True)
    procedure_id = Column(Integer, ForeignKey("procedures.id"), nullable=False)
    
    # Dados do agendamento
    data_hora = Column(DateTime, nullable=False, index=True)
    duracao_minutos = Column(Integer, nullable=False, default=30)
    
    # Integração com calendários externos
    id_evento_calendar = Column(String(255), nullable=True)  # Google Calendar / Feegow event ID
    
    # Status
    status = Column(
        SQLEnum(AppointmentStatus),
        nullable=False,
        default=AppointmentStatus.AGENDADO,
        index=True
    )
    
    # Observações
    observacoes = Column(Text, nullable=True)
    
    # Relacionamentos ORM
    tenant = relationship("Tenant", back_populates="appointments")
    contact = relationship("Contact", back_populates="appointments")
    procedure = relationship("Procedure", back_populates="appointments")
    reminder_logs = relationship("ReminderLog", back_populates="appointment", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Appointment {self.id}: {self.contact_id} - {self.procedure_id} @ {self.data_hora}>"
