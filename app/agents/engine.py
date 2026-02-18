"""
Agent Engine - LangGraph-based conversational AI agent
"""

from typing import Dict, Any, List, Optional, Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from sqlalchemy.ext.asyncio import AsyncSession
import json

from app.agents.memory import AgentMemory
from app.agents.humanizer import MessageHumanizer
from app.agents.voice import WhisperTranscription, ElevenLabsVoice
from app.agents.tools.calendar import CalendarTool
from app.agents.tools.procedures import ProceduresTool
from app.agents.tools.escalation import EscalationTool
from app.agents.tools.followup import FollowUpTool


class AgentState(TypedDict):
    """Estado do agente no LangGraph"""
    messages: List[Dict[str, Any]]
    tenant_id: int
    conversation_id: int
    contact_id: int
    agent_config: Dict[str, Any]
    patient_context: str
    should_escalate: bool
    actions_executed: List[str]
    final_response: Optional[List[Dict[str, Any]]]


class AgentEngine:
    """
    Engine principal do agente de IA usando LangGraph
    
    Fluxo:
    1. Recebe mensagem do usuário
    2. Carrega contexto (memória + info paciente)
    3. Processa com LLM
    4. Executa ferramentas se necessário
    5. Humaniza resposta (quebra + delays)
    6. Retorna mensagens para envio
    """
    
    def __init__(
        self,
        db: AsyncSession,
        tenant_id: int,
        conversation_id: int,
        contact_id: int,
        agent_config: Dict[str, Any]
    ):
        self.db = db
        self.tenant_id = tenant_id
        self.conversation_id = conversation_id
        self.contact_id = contact_id
        self.agent_config = agent_config
        
        # Componentes
        self.memory = AgentMemory(db, conversation_id)
        self.humanizer = MessageHumanizer()
        self.whisper = WhisperTranscription()
        self.elevenlabs = ElevenLabsVoice()
        
        # Ferramentas
        self.calendar_tool = CalendarTool(db, tenant_id)
        self.procedures_tool = ProceduresTool(db, tenant_id)
        self.escalation_tool = EscalationTool(db, conversation_id)
        self.followup_tool = FollowUpTool(tenant_id)
        
        # LLM
        self.llm = self._init_llm()
        
        # Graph
        self.graph = self._build_graph()
    
    def _init_llm(self):
        """Inicializa LLM baseado na configuração do agente"""
        model = self.agent_config.get("modelo", "gpt-4o")
        temperature = self.agent_config.get("temperatura", 0.7)
        
        if model.startswith("gpt"):
            return ChatOpenAI(
                model=model,
                temperature=temperature
            )
        elif model.startswith("claude"):
            return ChatAnthropic(
                model=model,
                temperature=temperature
            )
        else:
            # Default
            return ChatOpenAI(model="gpt-4o", temperature=0.7)
    
    def _build_graph(self) -> StateGraph:
        """Constrói o grafo LangGraph"""
        workflow = StateGraph(AgentState)
        
        # Nodes
        workflow.add_node("load_context", self._load_context)
        workflow.add_node("process_message", self._process_message)
        workflow.add_node("execute_tools", self._execute_tools)
        workflow.add_node("humanize_response", self._humanize_response)
        
        # Edges
        workflow.set_entry_point("load_context")
        workflow.add_edge("load_context", "process_message")
        workflow.add_conditional_edges(
            "process_message",
            self._should_use_tools,
            {
                "tools": "execute_tools",
                "respond": "humanize_response"
            }
        )
        workflow.add_edge("execute_tools", "process_message")
        workflow.add_edge("humanize_response", END)
        
        return workflow.compile()
    
    async def _load_context(self, state: AgentState) -> AgentState:
        """Carrega contexto do paciente e histórico"""
        context = await self.memory.get_context_for_llm(state["contact_id"])
        state["patient_context"] = context
        return state
    
    async def _process_message(self, state: AgentState) -> AgentState:
        """Processa mensagem com LLM"""
        # Montar system prompt
        system_prompt = self._build_system_prompt(state)
        
        # Montar mensagens
        messages = [SystemMessage(content=system_prompt)]
        
        # Adicionar histórico
        for msg in state["messages"]:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            else:
                messages.append(AIMessage(content=msg["content"]))
        
        # Chamar LLM
        response = await self.llm.ainvoke(messages)
        
        # Adicionar resposta ao estado
        state["messages"].append({
            "role": "assistant",
            "content": response.content
        })
        
        # Verificar se deve escalar
        if "escalar para humano" in response.content.lower():
            state["should_escalate"] = True
        
        return state
    
    def _build_system_prompt(self, state: AgentState) -> str:
        """Constrói system prompt personalizado"""
        base_prompt = self.agent_config.get("instrucoes", "")
        
        # Adicionar contexto do paciente
        prompt_parts = [base_prompt]
        
        if state.get("patient_context"):
            prompt_parts.append(f"\n\n{state['patient_context']}")
        
        # Adicionar instruções de ferramentas
        ferramentas_ativas = self.agent_config.get("ferramentas_ativas", [])
        if ferramentas_ativas:
            prompt_parts.append("\n\n=== FERRAMENTAS DISPONÍVEIS ===")
            
            if "buscar_horarios" in ferramentas_ativas:
                prompt_parts.append("- buscar_horarios_disponiveis(data, procedimento_id)")
            if "criar_agendamento" in ferramentas_ativas:
                prompt_parts.append("- criar_agendamento(contact_id, procedimento_id, data_hora, observacoes)")
            if "cancelar_agendamento" in ferramentas_ativas:
                prompt_parts.append("- cancelar_agendamento(id_evento, motivo)")
            if "buscar_procedimento" in ferramentas_ativas:
                prompt_parts.append("- buscar_informacoes_procedimento(nome_procedimento)")
            if "escalar" in ferramentas_ativas:
                prompt_parts.append("- escalar_para_humano(motivo, urgencia)")
        
        # Instruções de humanização
        prompt_parts.append("\n\n=== INSTRUÇÕES DE COMUNICAÇÃO ===")
        prompt_parts.append("- Use linguagem natural e humanizada")
        prompt_parts.append("- Seja empático e profissional")
        prompt_parts.append("- Mantenha respostas concisas (máximo 150 caracteres por mensagem)")
        prompt_parts.append("- Se precisar de mais informações, faça perguntas claras")
        
        return "\n".join(prompt_parts)
    
    def _should_use_tools(self, state: AgentState) -> str:
        """Decide se deve usar ferramentas ou responder diretamente"""
        last_message = state["messages"][-1]["content"]
        
        # Verificar se LLM solicitou uso de ferramenta
        # TODO: Implementar detecção de tool calls do LLM
        # Por enquanto, responder diretamente
        
        return "respond"
    
    async def _execute_tools(self, state: AgentState) -> AgentState:
        """Executa ferramentas solicitadas pelo LLM"""
        # TODO: Implementar execução de ferramentas
        # Parsear tool calls da resposta do LLM
        # Executar ferramentas correspondentes
        # Adicionar resultados ao estado
        
        return state
    
    async def _humanize_response(self, state: AgentState) -> AgentState:
        """Humaniza resposta (quebra mensagens + delays)"""
        last_message = state["messages"][-1]["content"]
        
        # Quebrar em mensagens menores
        humanized = self.humanizer.humanize(last_message)
        
        state["final_response"] = humanized
        return state
    
    async def process(
        self,
        message: Dict[str, Any],
        historico: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Processa mensagem do usuário
        
        Args:
            message: {tipo, conteudo, metadados}
            historico: Histórico de mensagens (opcional)
        
        Returns:
            {
                mensagens: [{conteudo, delay_ms, tipo}],
                acoes_executadas: [],
                deve_escalar: bool,
                metadados: {}
            }
        """
        # Processar mídia se necessário
        content = await self._process_media(message)
        
        # Carregar histórico se não fornecido
        if not historico:
            historico = await self.memory.get_conversation_history()
        
        # Montar estado inicial
        initial_state: AgentState = {
            "messages": historico + [{
                "role": "user",
                "content": content
            }],
            "tenant_id": self.tenant_id,
            "conversation_id": self.conversation_id,
            "contact_id": self.contact_id,
            "agent_config": self.agent_config,
            "patient_context": "",
            "should_escalate": False,
            "actions_executed": [],
            "final_response": None
        }
        
        # Executar graph
        final_state = await self.graph.ainvoke(initial_state)
        
        # Processar voz se necessário
        messages = final_state["final_response"] or []
        if self._should_use_voice():
            messages = await self._add_voice_to_messages(messages)
        
        return {
            "mensagens": messages,
            "acoes_executadas": final_state["actions_executed"],
            "deve_escalar": final_state["should_escalate"],
            "metadados": {
                "model": self.agent_config.get("modelo"),
                "total_messages": len(final_state["messages"])
            }
        }
    
    async def _process_media(self, message: Dict[str, Any]) -> str:
        """Processa mídia (imagem, áudio) e retorna texto"""
        tipo = message.get("tipo")
        conteudo = message.get("conteudo")
        
        if tipo == "audio":
            # Transcrever áudio
            audio_url = message.get("metadados", {}).get("midia_url")
            if audio_url:
                transcription = await self.whisper.transcribe_from_url(audio_url)
                return transcription
        
        elif tipo == "image":
            # TODO: Processar imagem com GPT-4o Vision
            # Por enquanto, retornar descrição
            return f"[Imagem recebida] {conteudo}"
        
        return conteudo
    
    def _should_use_voice(self) -> bool:
        """Verifica se deve usar voz na resposta"""
        # Verificar se tenant tem ElevenLabs configurado
        voice_config = self.agent_config.get("voz", {})
        return voice_config.get("ativo", False)
    
    async def _add_voice_to_messages(
        self,
        messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Adiciona áudio às mensagens"""
        voice_config = self.agent_config.get("voz", {})
        voice_id = voice_config.get("voice_id")
        
        if not voice_id:
            return messages
        
        # Adicionar áudio para cada mensagem
        for msg in messages:
            try:
                audio_base64 = await self.elevenlabs.text_to_speech_base64(
                    msg["conteudo"],
                    voice_id
                )
                msg["audio_base64"] = audio_base64
                msg["tipo"] = "audio"
            except Exception as e:
                print(f"Erro ao gerar áudio: {str(e)}")
        
        return messages


# Função helper para uso nos workers
async def process_message_with_agent(
    db: AsyncSession,
    tenant_id: int,
    conversation_id: int,
    contact_id: int,
    agent_config: Dict[str, Any],
    message: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Processa mensagem com agente IA
    
    Função helper para ser chamada pelos workers Celery
    """
    engine = AgentEngine(
        db=db,
        tenant_id=tenant_id,
        conversation_id=conversation_id,
        contact_id=contact_id,
        agent_config=agent_config
    )
    
    return await engine.process(message)
