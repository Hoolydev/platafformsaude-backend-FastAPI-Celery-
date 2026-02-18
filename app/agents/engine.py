"""
Agent Engine — LangGraph principal
"""

from typing import Any, Dict, List, Optional, TypedDict, Annotated
import operator

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.agents import memory as mem
from app.agents.humanizer import prepare_messages
from app.models.message import MessageOrigem, MessageTipo


# ─── State ────────────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    tenant_id: int
    conversation_id: int
    contact_id: int
    agent_config: Dict[str, Any]
    deve_escalar: bool
    respostas: List[Dict[str, Any]]


# ─── LLM factory ──────────────────────────────────────────────────────────────

def _get_llm(modelo: str):
    if modelo.startswith("claude"):
        return ChatAnthropic(
            model=modelo,
            api_key=settings.ANTHROPIC_API_KEY,
            temperature=0.7,
        )
    return ChatOpenAI(
        model=modelo or "gpt-4o",
        api_key=settings.OPENAI_API_KEY,
        temperature=0.7,
    )


# ─── Tools (LangChain @tool wrappers) ─────────────────────────────────────────
# As tools recebem db via closure quando o grafo é instanciado por run_agent()

def _build_tools(db: AsyncSession, tenant_id: int, conversation_id: int):

    @tool
    async def buscar_horarios(data: str, procedimento_id: Optional[int] = None) -> str:
        """Busca horários disponíveis na agenda. data no formato YYYY-MM-DD."""
        from datetime import date
        from app.agents.tools.calendar import buscar_horarios_disponiveis
        slots = await buscar_horarios_disponiveis(db, tenant_id, date.fromisoformat(data), procedimento_id)
        return str(slots) if slots else "Nenhum horário disponível para esta data."

    @tool
    async def criar_agendamento(procedimento_id: int, data_hora: str, titulo: str = "Consulta") -> str:
        """Cria agendamento. data_hora no formato ISO 8601."""
        from datetime import datetime
        from app.agents.tools.calendar import criar_agendamento as _criar
        result = await _criar(db, tenant_id, 0, procedimento_id, datetime.fromisoformat(data_hora), titulo)
        return str(result)

    @tool
    async def cancelar_agendamento(id_evento: str) -> str:
        """Cancela um agendamento pelo ID do evento."""
        from app.agents.tools.calendar import cancelar_agendamento as _cancelar
        result = await _cancelar(db, tenant_id, id_evento)
        return str(result)

    @tool
    async def buscar_procedimento(nome: str) -> str:
        """Busca informações de um procedimento pelo nome."""
        from app.agents.tools.procedures import buscar_procedimento as _buscar
        result = await _buscar(db, tenant_id, nome)
        return str(result) if result else "Procedimento não encontrado."

    @tool
    async def escalar(motivo: str) -> str:
        """Escala a conversa para um atendente humano quando necessário."""
        from app.agents.tools.escalation import escalar as _escalar
        result = await _escalar(db, tenant_id, conversation_id, motivo)
        return str(result)

    @tool
    async def agendar_followup(mensagem: str, data_hora: str) -> str:
        """Agenda envio de follow-up futuro. data_hora no formato ISO 8601."""
        from datetime import datetime
        from app.agents.tools.followup import agendar_followup as _agendar
        result = await _agendar(tenant_id, 0, mensagem, datetime.fromisoformat(data_hora), conversation_id)
        return str(result)

    return [buscar_horarios, criar_agendamento, cancelar_agendamento,
            buscar_procedimento, escalar, agendar_followup]


# ─── Graph nodes ──────────────────────────────────────────────────────────────

def _should_continue(state: AgentState):
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return END


async def _agent_node(state: AgentState, llm_with_tools):
    response = await llm_with_tools.ainvoke(state["messages"])
    return {"messages": [response]}


def _collect_response(state: AgentState) -> Dict[str, Any]:
    """Coleta a resposta final do agente e humaniza."""
    last = state["messages"][-1]
    content = last.content if hasattr(last, "content") else str(last)

    deve_escalar = "escalar" in content.lower() or state.get("deve_escalar", False)
    mensagens = prepare_messages(content)

    return {
        "respostas": mensagens,
        "deve_escalar": deve_escalar,
    }


# ─── Public API ───────────────────────────────────────────────────────────────

async def run_agent(
    db: AsyncSession,
    tenant_id: int,
    conversation_id: int,
    contact_id: int,
    message: str,
    agent_config: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Executa o agente LangGraph para uma mensagem recebida.

    Returns:
        {
            "mensagens": [{"conteudo": str, "delay_ms": int}],
            "deve_escalar": bool
        }
    """
    modelo = agent_config.get("modelo_llm", "gpt-4o")
    instrucoes = agent_config.get("instrucoes", "Você é um assistente de saúde prestativo.")

    # Busca histórico
    historico = await mem.get_history(db, conversation_id, limit=20)
    contact_info = await mem.get_contact_info(db, contact_id)

    # Monta system prompt
    system_content = instrucoes
    if contact_info:
        system_content += (
            f"\n\nInformações do contato:\n"
            f"Nome: {contact_info.get('nome', 'Desconhecido')}\n"
            f"Telefone: {contact_info.get('telefone', '')}\n"
            f"Dados adicionais: {contact_info.get('metadados', {})}"
        )

    # Converte histórico para mensagens LangChain
    lc_messages: List[BaseMessage] = [SystemMessage(content=system_content)]
    for h in historico:
        if h.origem == MessageOrigem.cliente:
            lc_messages.append(HumanMessage(content=h.conteudo))
        else:
            lc_messages.append(AIMessage(content=h.conteudo))

    # Adiciona mensagem atual
    lc_messages.append(HumanMessage(content=message))

    # Salva mensagem do cliente
    await mem.save_message(db, conversation_id, tenant_id, MessageOrigem.cliente, message)

    # Monta tools e LLM
    tools = _build_tools(db, tenant_id, conversation_id)
    llm = _get_llm(modelo)
    llm_with_tools = llm.bind_tools(tools)

    # Monta grafo LangGraph
    tool_node = ToolNode(tools)

    async def agent_node(state: AgentState):
        return await _agent_node(state, llm_with_tools)

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", _should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")
    compiled = graph.compile()

    # Executa
    initial_state: AgentState = {
        "messages": lc_messages,
        "tenant_id": tenant_id,
        "conversation_id": conversation_id,
        "contact_id": contact_id,
        "agent_config": agent_config,
        "deve_escalar": False,
        "respostas": [],
    }

    final_state = await compiled.ainvoke(initial_state)
    result = _collect_response(final_state)

    # Salva resposta do agente
    for msg in result["respostas"]:
        await mem.save_message(
            db, conversation_id, tenant_id,
            MessageOrigem.agente, msg["conteudo"],
        )

    return {
        "mensagens": result["respostas"],
        "deve_escalar": result["deve_escalar"],
    }
