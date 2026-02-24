"""
Service: Flow Executor
Handles the execution of node-based chatbot flows.
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.flow import Flow, FlowNode, FlowEdge
from app.models.conversation import Conversation
from app.models.message import Message, MessageOrigem, MessageTipo
from app.models.contact import Contact

class FlowExecutor:
    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id

    async def execute_step(self, conversation: Conversation, contact: Contact, input_message: str):
        """
        Executa o próximo passo do fluxo para uma conversa.
        """
        if not conversation.flow_id:
            return None

        # 1. Obter o nó atual ou o nó inicial
        if not conversation.current_node_id:
            # Pegar primeiro nó do fluxo (geralmente do tipo "inicio")
            result = await self.db.execute(
                select(FlowNode).where(
                    FlowNode.flow_id == conversation.flow_id,
                    FlowNode.tipo == "inicio"
                )
            )
            node = result.scalar_one_or_none()
            
            if not node:
                result = await self.db.execute(
                    select(FlowNode).where(
                        FlowNode.flow_id == conversation.flow_id
                    ).order_by(FlowNode.id.asc())
                )
                node = result.scalars().first()
        else:
            # Verificar se é uma resposta a uma pergunta ou menu
            result = await self.db.execute(
                select(FlowNode).where(FlowNode.id == conversation.current_node_id)
            )
            current_node = result.scalar_one_or_none()
            
            if current_node and current_node.tipo in ["question", "menu"]:
                # Encontrar aresta que corresponde à resposta
                node = await self._find_next_node(current_node.id, input_message)
            else:
                # Transição direta
                node = await self._find_next_node(conversation.current_node_id)

        if not node:
             return None

        # 2. Processar o nó atual
        return await self._process_node(node, conversation, contact)

    async def _find_next_node(self, source_node_id: int, input_text: Optional[str] = None) -> Optional[FlowNode]:
        """
        Encontra o próximo nó com base nas arestas.
        """
        result = await self.db.execute(
            select(FlowEdge).where(FlowEdge.source_node_id == source_node_id)
        )
        edges = result.scalars().all()
        
        if not edges:
            return None

        # Se houver condição, tenta bater
        if input_text:
            input_text_lower = input_text.lower()
            for edge in edges:
                if edge.condicao and edge.condicao.lower() in input_text_lower:
                    res = await self.db.execute(
                        select(FlowNode).where(FlowNode.id == edge.target_node_id)
                    )
                    return res.scalar_one_or_none()

        # Se não bater nada ou não houver input_text, pega a primeira aresta sem condição (padrão)
        for edge in edges:
            if not edge.condicao:
                res = await self.db.execute(
                    select(FlowNode).where(FlowNode.id == edge.target_node_id)
                )
                return res.scalar_one_or_none()

        return None

    async def _process_node(self, node: FlowNode, conversation: Conversation, contact: Contact):
        """
        Executa a lógica de um nó específico.
        """
        conversation.current_node_id = node.id
        self.db.add(conversation)
        await self.db.flush()

        result = {"node_type": node.tipo, "response": None, "actions": []}
        config = node.configuracoes or {}

        if node.tipo in ["message", "inicio"]:
            result["response"] = config.get("texto", "Olá!")
            
        elif node.tipo == "menu":
            texto = config.get("texto", "Escolha uma opção:")
            opcoes = config.get("opcoes", [])
            if opcoes:
                texto += "\n" + "\n".join([f"{i+1}. {opt.get('label')}" for i, opt in enumerate(opcoes)])
            result["response"] = texto

        elif node.tipo == "question":
            result["response"] = config.get("pergunta", "Qual sua dúvida?")

        elif node.tipo == "ia":
            result["response"] = "USE_AGENT"

        elif node.tipo == "action":
            action_type = config.get("action_type")
            if action_type == "transfer":
                conversation.status = "assumido"
                result["actions"].append("transfer")
            elif action_type == "conclude":
                 conversation.status = "concluido"
                 result["actions"].append("conclude")
            
            # Após ação, tenta ir para o próximo nó automaticamente
            next_node = await self._find_next_node(node.id)
            if next_node:
                return await self._process_node(next_node, conversation, contact)

        return result
