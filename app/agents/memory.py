"""
Memory - Memória persistente para agentes IA
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime
import json

from app.models.message import Message
from app.models.contact import Contact
from app.models.conversation import Conversation


class AgentMemory:
    """
    Gerencia memória do agente:
    - Memória de janela (últimas N mensagens)
    - Memória persistente (informações do paciente)
    """
    
    def __init__(
        self,
        db: AsyncSession,
        conversation_id: int,
        window_size: int = 20
    ):
        self.db = db
        self.conversation_id = conversation_id
        self.window_size = window_size
    
    async def get_conversation_history(self) -> List[Dict[str, Any]]:
        """
        Busca histórico das últimas N mensagens da conversa
        
        Returns:
            Lista de mensagens formatadas para o LLM
        """
        result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == self.conversation_id)
            .order_by(desc(Message.created_at))
            .limit(self.window_size)
        )
        messages = result.scalars().all()
        
        # Inverter para ordem cronológica
        messages = list(reversed(messages))
        
        # Formatar para LLM
        formatted = []
        for msg in messages:
            role = self._map_origin_to_role(msg.origem.value)
            formatted.append({
                "role": role,
                "content": msg.conteudo,
                "timestamp": msg.created_at.isoformat(),
                "tipo": msg.tipo.value,
                "metadados": msg.metadados
            })
        
        return formatted
    
    def _map_origin_to_role(self, origem: str) -> str:
        """Mapeia origem da mensagem para role do LLM"""
        mapping = {
            "cliente": "user",
            "agente": "assistant",
            "atendente": "assistant"
        }
        return mapping.get(origem, "user")
    
    async def get_patient_info(self, contact_id: int) -> Dict[str, Any]:
        """
        Busca informações persistentes do paciente
        
        Returns:
            Dicionário com informações do paciente
        """
        result = await self.db.execute(
            select(Contact).where(Contact.id == contact_id)
        )
        contact = result.scalar_one_or_none()
        
        if not contact:
            return {}
        
        # Buscar histórico de conversas
        result = await self.db.execute(
            select(Conversation)
            .where(Conversation.contact_id == contact_id)
            .order_by(desc(Conversation.created_at))
            .limit(5)
        )
        past_conversations = result.scalars().all()
        
        return {
            "nome": contact.nome,
            "telefone": contact.telefone,
            "email": contact.email,
            "tags": contact.tags,
            "metadados": contact.metadados,
            "total_conversas": len(past_conversations),
            "ultima_conversa": past_conversations[0].created_at.isoformat() if past_conversations else None,
            "historico_assuntos": [conv.assunto for conv in past_conversations if conv.assunto]
        }
    
    async def save_patient_info(self, contact_id: int, info: Dict[str, Any]):
        """
        Salva informações do paciente nos metadados
        
        Args:
            contact_id: ID do contato
            info: Dicionário com informações a salvar
        """
        result = await self.db.execute(
            select(Contact).where(Contact.id == contact_id)
        )
        contact = result.scalar_one_or_none()
        
        if contact:
            # Merge com metadados existentes
            current_metadata = contact.metadados or {}
            current_metadata.update(info)
            contact.metadados = current_metadata
            
            await self.db.commit()
    
    async def get_context_for_llm(self, contact_id: int) -> str:
        """
        Monta contexto completo para o LLM
        
        Returns:
            String formatada com contexto do paciente e histórico
        """
        patient_info = await self.get_patient_info(contact_id)
        history = await self.get_conversation_history()
        
        context_parts = []
        
        # Informações do paciente
        if patient_info:
            context_parts.append("=== INFORMAÇÕES DO PACIENTE ===")
            if patient_info.get("nome"):
                context_parts.append(f"Nome: {patient_info['nome']}")
            if patient_info.get("email"):
                context_parts.append(f"Email: {patient_info['email']}")
            if patient_info.get("metadados"):
                metadata = patient_info["metadados"]
                if metadata.get("plano_saude"):
                    context_parts.append(f"Plano de Saúde: {metadata['plano_saude']}")
                if metadata.get("data_nascimento"):
                    context_parts.append(f"Data de Nascimento: {metadata['data_nascimento']}")
            
            if patient_info.get("total_conversas", 0) > 0:
                context_parts.append(f"\nPaciente já teve {patient_info['total_conversas']} conversas anteriores")
                if patient_info.get("historico_assuntos"):
                    context_parts.append(f"Assuntos anteriores: {', '.join(patient_info['historico_assuntos'][:3])}")
        
        # Histórico recente
        if history:
            context_parts.append("\n=== HISTÓRICO DA CONVERSA ===")
            for msg in history[-5:]:  # Últimas 5 mensagens
                role = "Paciente" if msg["role"] == "user" else "Você"
                context_parts.append(f"{role}: {msg['content']}")
        
        return "\n".join(context_parts)


class ConversationSummarizer:
    """Cria resumos de conversas para memória de longo prazo"""
    
    @staticmethod
    async def summarize_conversation(
        db: AsyncSession,
        conversation_id: int,
        llm_client: Any = None
    ) -> str:
        """
        Cria resumo da conversa usando LLM
        
        Args:
            db: Sessão do banco
            conversation_id: ID da conversa
            llm_client: Cliente do LLM (OpenAI, Anthropic, etc)
        
        Returns:
            Resumo da conversa
        """
        # Buscar todas as mensagens
        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
        )
        messages = result.scalars().all()
        
        if not messages:
            return ""
        
        # Formatar mensagens
        conversation_text = []
        for msg in messages:
            role = "Paciente" if msg.origem.value == "cliente" else "Atendente"
            conversation_text.append(f"{role}: {msg.conteudo}")
        
        full_text = "\n".join(conversation_text)
        
        # TODO: Usar LLM para criar resumo
        # Por enquanto, retornar primeiras e últimas mensagens
        if len(messages) > 10:
            summary = f"Conversa com {len(messages)} mensagens. "
            summary += f"Início: {messages[0].conteudo[:100]}... "
            summary += f"Fim: {messages[-1].conteudo[:100]}..."
            return summary
        
        return full_text
