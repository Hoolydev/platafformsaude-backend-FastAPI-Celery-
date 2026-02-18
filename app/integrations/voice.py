"""
Voice Integrations - ElevenLabs TTS e Retell AI
"""

from typing import Optional, Dict, Any
import httpx
import hashlib
from datetime import datetime, timedelta
import os
import io

from app.config import settings


class ElevenLabsSender:
    """
    Cliente para ElevenLabs Text-to-Speech
    
    Features:
    - Conversão de texto para áudio
    - Cache de áudios gerados (MinIO)
    - Signed URLs temporárias
    """
    
    def __init__(self):
        self.api_key = settings.ELEVENLABS_API_KEY
        self.base_url = "https://api.elevenlabs.io/v1"
        
    async def text_to_speech(
        self,
        text: str,
        voice_id: str,
        tenant_id: int,
        model_id: str = "eleven_multilingual_v2"
    ) -> Dict[str, Any]:
        """
        Converte texto para áudio
        
        Args:
            text: Texto para converter
            voice_id: ID da voz no ElevenLabs
            tenant_id: ID do tenant
            model_id: Modelo de voz
        
        Returns:
            {
                "audio_url": "https://...",
                "cached": bool,
                "duration_ms": int
            }
        """
        # Verificar cache
        cache_key = self._generate_cache_key(text, voice_id)
        cached_url = await self._get_from_cache(cache_key, tenant_id)
        
        if cached_url:
            return {
                "audio_url": cached_url,
                "cached": True,
                "duration_ms": 0  # Não calculamos para cache
            }
        
        # Gerar áudio
        audio_bytes = await self._generate_audio(text, voice_id, model_id)
        
        # Salvar no MinIO
        audio_url = await self._save_to_minio(
            audio_bytes,
            cache_key,
            tenant_id
        )
        
        return {
            "audio_url": audio_url,
            "cached": False,
            "duration_ms": len(audio_bytes) // 16  # Aproximação
        }
    
    async def _generate_audio(
        self,
        text: str,
        voice_id: str,
        model_id: str
    ) -> bytes:
        """Gera áudio via API ElevenLabs"""
        url = f"{self.base_url}/text-to-speech/{voice_id}"
        
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "text": text,
            "model_id": model_id,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "style": 0.0,
                "use_speaker_boost": True
            }
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.content
    
    def _generate_cache_key(self, text: str, voice_id: str) -> str:
        """Gera chave de cache baseada no texto e voz"""
        content = f"{text}:{voice_id}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    async def _get_from_cache(
        self,
        cache_key: str,
        tenant_id: int
    ) -> Optional[str]:
        """Busca áudio no cache (MinIO)"""
        from app.services.storage import get_minio_client
        
        try:
            minio_client = get_minio_client()
            bucket_name = f"tenant-{tenant_id}-voice-cache"
            object_name = f"{cache_key}.mp3"
            
            # Verificar se existe
            try:
                stat = minio_client.stat_object(bucket_name, object_name)
                
                # Verificar se foi criado hoje
                if stat.last_modified.date() == datetime.utcnow().date():
                    # Gerar signed URL (1 hora)
                    url = minio_client.presigned_get_object(
                        bucket_name,
                        object_name,
                        expires=timedelta(hours=1)
                    )
                    return url
            except:
                return None
        except Exception as e:
            print(f"Erro ao buscar cache: {str(e)}")
            return None
    
    async def _save_to_minio(
        self,
        audio_bytes: bytes,
        cache_key: str,
        tenant_id: int
    ) -> str:
        """Salva áudio no MinIO e retorna signed URL"""
        from app.services.storage import get_minio_client
        
        minio_client = get_minio_client()
        bucket_name = f"tenant-{tenant_id}-voice-cache"
        object_name = f"{cache_key}.mp3"
        
        # Criar bucket se não existir
        if not minio_client.bucket_exists(bucket_name):
            minio_client.make_bucket(bucket_name)
        
        # Upload
        minio_client.put_object(
            bucket_name,
            object_name,
            io.BytesIO(audio_bytes),
            length=len(audio_bytes),
            content_type="audio/mpeg"
        )
        
        # Gerar signed URL (1 hora)
        url = minio_client.presigned_get_object(
            bucket_name,
            object_name,
            expires=timedelta(hours=1)
        )
        
        return url


class RetellAIHandler:
    """
    Handler para integração com Retell AI
    
    Processa webhooks de ligações em tempo real
    """
    
    def __init__(self):
        self.api_key = settings.RETELL_API_KEY
        self.base_url = "https://api.retellai.com/v1"
    
    async def process_webhook(
        self,
        tenant_id: int,
        agent_id: int,
        webhook_data: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Processa webhook do Retell AI
        
        Args:
            tenant_id: ID do tenant
            agent_id: ID do agente
            webhook_data: Dados do webhook
        
        Returns:
            {"response": "texto da resposta"}
        """
        from sqlalchemy.ext.asyncio import AsyncSession
        from sqlalchemy import select, and_
        from app.database import AsyncSessionLocal
        from app.models.agent import Agent
        from app.models.contact import Contact
        from app.models.conversation import Conversation, ConversationStatus
        from app.models.message import Message, MessageOrigin, MessageType
        from app.agents.engine import AgentEngine
        
        call_id = webhook_data.get("call_id")
        transcript = webhook_data.get("transcript", "")
        turn = webhook_data.get("turn", 0)
        is_final = webhook_data.get("is_final", False)
        
        # Processar apenas turnos finais
        if not is_final:
            return {"response": ""}
        
        async with AsyncSessionLocal() as db:
            # Buscar agente
            result = await db.execute(
                select(Agent).where(
                    and_(
                        Agent.id == agent_id,
                        Agent.tenant_id == tenant_id
                    )
                )
            )
            agent = result.scalar_one_or_none()
            
            if not agent:
                return {"response": "Desculpe, não consegui processar sua solicitação."}
            
            # Buscar ou criar contato (usar call_id como identificador temporário)
            phone = webhook_data.get("customer_phone", f"retell_{call_id}")
            
            result = await db.execute(
                select(Contact).where(
                    and_(
                        Contact.tenant_id == tenant_id,
                        Contact.telefone == phone
                    )
                )
            )
            contact = result.scalar_one_or_none()
            
            if not contact:
                contact = Contact(
                    tenant_id=tenant_id,
                    telefone=phone,
                    nome=webhook_data.get("customer_name"),
                    metadados={"source": "retell_ai", "call_id": call_id}
                )
                db.add(contact)
                await db.flush()
            
            # Buscar ou criar conversa
            result = await db.execute(
                select(Conversation).where(
                    and_(
                        Conversation.tenant_id == tenant_id,
                        Conversation.contact_id == contact.id,
                        Conversation.status == ConversationStatus.ATIVO
                    )
                ).order_by(Conversation.created_at.desc()).limit(1)
            )
            conversation = result.scalar_one_or_none()
            
            if not conversation:
                conversation = Conversation(
                    tenant_id=tenant_id,
                    contact_id=contact.id,
                    canal="retell_ai",
                    status=ConversationStatus.ATIVO,
                    agente_ativo=True,
                    agent_id=agent.id,
                    assunto="Ligação via Retell AI"
                )
                db.add(conversation)
                await db.flush()
            
            # Salvar mensagem do cliente
            message_cliente = Message(
                conversation_id=conversation.id,
                tenant_id=tenant_id,
                origem=MessageOrigin.CLIENTE,
                tipo=MessageType.TEXTO,
                conteudo=transcript,
                metadados={
                    "source": "retell_ai",
                    "call_id": call_id,
                    "turn": turn
                }
            )
            db.add(message_cliente)
            await db.flush()
            
            # Processar com agent engine
            engine = AgentEngine(agent, db)
            response = await engine.process_message(
                conversation_id=conversation.id,
                message_text=transcript,
                message_type="text"
            )
            
            # Extrair texto da resposta
            response_text = ""
            if isinstance(response, list):
                response_text = " ".join([r.get("conteudo", "") for r in response])
            elif isinstance(response, dict):
                response_text = response.get("conteudo", "")
            else:
                response_text = str(response)
            
            # Salvar resposta do agente
            message_agente = Message(
                conversation_id=conversation.id,
                tenant_id=tenant_id,
                origem=MessageOrigin.AGENTE,
                tipo=MessageType.TEXTO,
                conteudo=response_text,
                metadados={
                    "source": "retell_ai",
                    "call_id": call_id,
                    "turn": turn
                }
            )
            db.add(message_agente)
            await db.commit()
            
            return {"response": response_text}
    
    async def process_call_ended(
        self,
        tenant_id: int,
        call_data: Dict[str, Any]
    ):
        """
        Processa fim de ligação
        
        Salva transcrição completa e dispara follow-up se necessário
        """
        from sqlalchemy.ext.asyncio import AsyncSession
        from sqlalchemy import select, and_
        from app.database import AsyncSessionLocal
        from app.models.conversation import Conversation, ConversationStatus
        from app.models.appointment import Appointment, AppointmentStatus
        from app.workers.lead_recovery import criar_lead_recovery
        from app.models.lead_recovery import LeadRecoveryTrigger
        
        call_id = call_data.get("call_id")
        full_transcript = call_data.get("transcript", "")
        duration_seconds = call_data.get("duration_seconds", 0)
        
        async with AsyncSessionLocal() as db:
            # Buscar conversa pelo call_id
            result = await db.execute(
                select(Conversation).join(
                    Conversation.messages
                ).where(
                    and_(
                        Conversation.tenant_id == tenant_id,
                        Message.metadados["call_id"].astext == call_id
                    )
                ).limit(1)
            )
            conversation = result.scalar_one_or_none()
            
            if not conversation:
                print(f"Conversa não encontrada para call_id {call_id}")
                return
            
            # Atualizar resumo da conversa
            conversation.resumo = f"Ligação via Retell AI - Duração: {duration_seconds}s\n\n{full_transcript[:500]}"
            conversation.status = ConversationStatus.CONCLUIDO
            
            # Verificar se houve agendamento
            result = await db.execute(
                select(Appointment).where(
                    and_(
                        Appointment.conversation_id == conversation.id,
                        Appointment.status.in_([
                            AppointmentStatus.AGENDADO,
                            AppointmentStatus.CONFIRMADO
                        ])
                    )
                )
            )
            has_appointment = result.scalar_one_or_none() is not None
            
            # Se não houve agendamento, criar lead recovery
            if not has_appointment:
                await criar_lead_recovery(
                    db,
                    tenant_id=tenant_id,
                    contact_id=conversation.contact_id,
                    conversation_id=conversation.id,
                    trigger_tipo=LeadRecoveryTrigger.INATIVO,
                    delay_hours=24
                )
            
            await db.commit()
            
            print(f"Ligação {call_id} finalizada - Duração: {duration_seconds}s")


async def detect_voice_preference(
    db,
    contact_id: int,
    message_type: str
):
    """
    Detecta preferência de voz do cliente
    
    Args:
        db: Sessão do banco
        contact_id: ID do contato
        message_type: Tipo da mensagem (audio/text)
    """
    from sqlalchemy import select, and_, func
    from app.models.message import Message, MessageOrigin, MessageType
    from app.models.contact import Contact
    
    # Buscar últimas 5 mensagens do cliente
    result = await db.execute(
        select(Message).where(
            and_(
                Message.contact_id == contact_id,
                Message.origem == MessageOrigin.CLIENTE
            )
        ).order_by(Message.created_at.desc()).limit(5)
    )
    recent_messages = result.scalars().all()
    
    if len(recent_messages) < 3:
        return  # Não há dados suficientes
    
    # Contar áudios consecutivos
    audio_count = sum(1 for msg in recent_messages[:3] if msg.tipo == MessageType.AUDIO)
    
    # Atualizar preferência
    result = await db.execute(
        select(Contact).where(Contact.id == contact_id)
    )
    contact = result.scalar_one_or_none()
    
    if contact:
        metadados = contact.metadados or {}
        
        if audio_count >= 3:
            metadados["preferencia_voz"] = True
        elif message_type == "text" and recent_messages[0].tipo == MessageType.AUDIO:
            # Cliente enviou texto após receber áudio
            metadados["preferencia_voz"] = False
        
        contact.metadados = metadados
        await db.commit()
