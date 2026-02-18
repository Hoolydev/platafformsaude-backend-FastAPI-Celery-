"""
ReminderLog Model - Log de lembretes enviados
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.database import Base


class ReminderType(enum.Enum):
    """Tipo de lembrete"""
    CONFIRMACAO = "confirmacao"  # Imediato após agendamento
    LEMBRETE_24H = "lembrete_24h"  # 24 horas antes
    LEMBRETE_2H = "lembrete_2h"  # 2 horas antes


class ReminderStatus(enum.Enum):
    """Status do envio do lembrete"""
    ENVIADO = "enviado"
    ERRO = "erro"
    PENDENTE = "pendente"


class ReminderLog(Base):
    """
    Log de lembretes enviados
    
    Evita duplicatas e rastreia envios
    """
    __tablename__ = "reminder_logs"
    
    # Relacionamento
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=False, index=True)
    
    # Tipo de lembrete
    tipo_lembrete = Column(
        SQLEnum(ReminderType),
        nullable=False,
        index=True
    )
    
    # Status do envio
    status = Column(
        SQLEnum(ReminderStatus),
        nullable=False,
        default=ReminderStatus.PENDENTE
    )
    
    # Timestamp do envio
    enviado_em = Column(DateTime, nullable=True)
    
    # Erro (se houver)
    erro = Column(Text, nullable=True)
    
    # Relacionamento ORM
    appointment = relationship("Appointment", back_populates="reminder_logs")
    
    def __repr__(self):
        return f"<ReminderLog {self.id}: {self.tipo_lembrete.value} - {self.status.value}>"
