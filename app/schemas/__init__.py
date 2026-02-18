"""
Schemas package - Pydantic schemas para validação
"""

# Importar todos os schemas aqui para facilitar uso
from app.schemas.tenant import TenantCreate, TenantUpdate, TenantResponse
from app.schemas.user import UserCreate, UserUpdate, UserResponse, UserLogin
from app.schemas.auth import Token, TokenRefresh
from app.schemas.contact import ContactCreate, ContactUpdate, ContactResponse
from app.schemas.conversation import ConversationCreate, ConversationUpdate, ConversationResponse
from app.schemas.message import MessageCreate, MessageResponse
from app.schemas.agent import AgentCreate, AgentUpdate, AgentResponse, AgentToolCreate
from app.schemas.procedure import ProcedureCreate, ProcedureUpdate, ProcedureResponse

__all__ = [
    "TenantCreate", "TenantUpdate", "TenantResponse",
    "UserCreate", "UserUpdate", "UserResponse", "UserLogin",
    "Token", "TokenRefresh",
    "ContactCreate", "ContactUpdate", "ContactResponse",
    "ConversationCreate", "ConversationUpdate", "ConversationResponse",
    "MessageCreate", "MessageResponse",
    "AgentCreate", "AgentUpdate", "AgentResponse", "AgentToolCreate",
    "ProcedureCreate", "ProcedureUpdate", "ProcedureResponse",
]
