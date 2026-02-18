"""
Model: Appointment
"""

import enum
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Text
from sqlalchemy.sql import func
from app.database import Base


class AppointmentStatus(str, enum.Enum):
    agendado = "agendado"
    confirmado = "confirmado"
    cancelado = "cancelado"
    realizado = "realizado"
    faltou = "faltou"


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=False, index=True)
    procedure_id = Column(Integer, ForeignKey("procedures.id"), nullable=True)
    data_hora = Column(DateTime(timezone=True), nullable=False, index=True)
    duracao_minutos = Column(Integer, default=30)
    id_evento_calendar = Column(String(255))
    status = Column(Enum(AppointmentStatus), default=AppointmentStatus.agendado, nullable=False)
    observacoes = Column(Text)
    criado_em = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
