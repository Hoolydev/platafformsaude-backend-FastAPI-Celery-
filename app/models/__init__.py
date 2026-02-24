"""
Models — importa todos para que o Alembic detecte as tabelas
"""

from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.models.contact import Contact
from app.models.conversation import Conversation, ConversationStatus
from app.models.message import Message, MessageOrigem, MessageTipo
from app.models.agent import Agent, AgentTool
from app.models.procedure import Procedure
from app.models.whatsapp import WhatsappConnection, WhatsappProvider
from app.models.calendar import CalendarConnection, CalendarProvider
from app.models.appointment import Appointment, AppointmentStatus
from app.models.reminder_log import ReminderLog
from app.models.lead_recovery import LeadRecovery, LeadRecoveryStatus, LeadTriggerTipo
from app.models.flow import Flow, FlowNode, FlowEdge

__all__ = [
    "Tenant",
    "User", "UserRole",
    "Contact",
    "Conversation", "ConversationStatus",
    "Message", "MessageOrigem", "MessageTipo",
    "Agent", "AgentTool",
    "Procedure",
    "WhatsappConnection", "WhatsappProvider",
    "CalendarConnection", "CalendarProvider",
    "Appointment", "AppointmentStatus",
    "ReminderLog",
    "LeadRecovery", "LeadRecoveryStatus", "LeadTriggerTipo",
    "Flow", "FlowNode", "FlowEdge",
]
