"""
Model: ReminderLog
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from app.database import Base


class ReminderLog(Base):
    __tablename__ = "reminder_logs"

    id = Column(Integer, primary_key=True, index=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=False, index=True)
    tipo_lembrete = Column(String(20), nullable=False)  # "24h" | "2h"
    enviado_em = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    status = Column(String(20), default="enviado")  # enviado | falhou
    erro = Column(Text)
