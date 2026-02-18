"""
Models package - Todos os modelos SQLAlchemy
"""

from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.models.contact import Contact
from app.models.conversation import Conversation, ConversationStatus
from app.models.message import Message, MessageOrigin, MessageType
from app.models.agent import Agent, AgentTool
from app.models.procedure import Procedure
from app.models.connection import WhatsappConnection, CalendarConnection, WhatsappProvider, CalendarProvider
from app.models.appointment import Appointment, AppointmentStatus
from app.models.reminder_log import ReminderLog, ReminderType, ReminderStatus
from app.models.lead_recovery import LeadRecovery, LeadRecoveryTrigger, LeadRecoveryStatus

__all__ = [
    "Tenant",
    "User",
    "UserRole",
    "Contact",
    "Conversation",
    "ConversationStatus",
    "Message",
    "MessageOrigin",
    "MessageType",
    "Agent",
    "AgentTool",
    "Procedure",
    "WhatsappConnection",
    "CalendarConnection",
]
