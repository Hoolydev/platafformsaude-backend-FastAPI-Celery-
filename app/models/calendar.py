"""
Model: CalendarConnection
"""

import enum
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import JSONB
from app.database import Base


class CalendarProvider(str, enum.Enum):
    google = "google"
    feegow = "feegow"


class CalendarConnection(Base):
    __tablename__ = "calendar_connections"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    provider = Column(Enum(CalendarProvider), nullable=False)
    credenciais = Column(JSONB, default={})
    id_agenda = Column(String(255))
    ativo = Column(Boolean, default=True, nullable=False)
