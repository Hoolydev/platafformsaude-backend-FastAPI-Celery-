# 🎙️ Módulo de Gestão de Ligações por Voz - Documentação

## Visão Geral

Sistema completo de gestão de voz com dois modos de operação: **Resposta em Áudio** (ElevenLabs TTS) e **Ligação Completa** (Retell AI), com detecção automática de preferência do cliente.

## 🎯 Funcionalidades

### Modo 1: Resposta em Áudio (ElevenLabs)

✅ **Conversão TTS**: Agente processa texto e converte para áudio  
✅ **Cache Inteligente**: Áudios salvos no MinIO, reutilizados se mesma frase  
✅ **Detecção Automática**: Se cliente envia áudio, responde em áudio  
✅ **Configurável**: Toggle por tenant "responder em áudio"  
✅ **Preferência por Contato**: Alguns clientes preferem texto

### Modo 2: Ligação Completa (Retell AI)

✅ **Webhook em Tempo Real**: Recebe transcrição durante ligação  
✅ **Processamento com Agent Engine**: Usa mesma IA do chat  
✅ **Salvamento no CRM**: Transcrição completa salva como conversa  
✅ **Follow-up Automático**: Se não agendou, cria lead recovery  
✅ **Criação de Contato**: Cria contato automaticamente se não existir

## 📊 Configuração por Tenant

### Modelo WhatsappConnection

```python
class WhatsappConnection(Base):
    # Configurações de voz
    modo_voz: str  # desabilitado, apenas_audio, retell
    elevenlabs_voice_id: str  # ID da voz no ElevenLabs
    retell_agent_id: str  # ID do agente no Retell AI
```

### Preferência por Contato

Salvo em `Contact.metadados`:

```json
{
  "preferencia_voz": true,  // Cliente prefere áudio
  "source": "retell_ai",
  "call_id": "abc123"
}
```

## 🔄 Detecção Automática de Preferência

### Lógica

```python
# Se cliente enviou 3+ áudios seguidos
if audio_count >= 3:
    metadados["preferencia_voz"] = True

# Se cliente enviou texto após receber áudio
if message_type == "text" and last_response_was_audio:
    metadados["preferencia_voz"] = False
```

### Aplicação

```python
async def _should_respond_audio():
    # 1. Verificar modo_voz da conexão
    if connection.modo_voz != "apenas_audio":
        return False
    
    # 2. Verificar preferência do contato
    if contact.metadados.get("preferencia_voz") is not None:
        return contact.metadados["preferencia_voz"]
    
    # 3. Se cliente enviou áudio, responder em áudio
    if message_type == "audio":
        return True
    
    return False
```

## 🎙️ ElevenLabs TTS

### Classe ElevenLabsSender

```python
from app.integrations.voice import ElevenLabsSender

sender = ElevenLabsSender()

result = await sender.text_to_speech(
    text="Olá! Como posso ajudar?",
    voice_id="21m00Tcm4TlvDq8ikWAM",  # Rachel
    tenant_id=1
)

# Retorna:
{
    "audio_url": "https://minio.../abc123.mp3",
    "cached": False,
    "duration_ms": 2500
}
```

### Cache MinIO

**Estrutura**:
- Bucket: `tenant-{tenant_id}-voice-cache`
- Objeto: `{sha256(text+voice_id)}.mp3`
- Validade: 1 dia (reutiliza se criado hoje)
- Signed URL: 1 hora de validade

**Fluxo**:
```
1. Gerar cache_key = sha256("texto:voice_id")
   ↓
2. Verificar se existe no MinIO
   ├─ Existe e criado hoje → Retornar signed URL
   └─ Não existe → Gerar áudio
   ↓
3. Chamar API ElevenLabs
   ↓
4. Salvar no MinIO
   ↓
5. Retornar signed URL
```

## 📞 Retell AI Integration

### Endpoints

#### POST /integrations/retell/webhook/{tenant_id}/{agent_id}

**Payload**:
```json
{
  "call_id": "abc123",
  "transcript": "Quero agendar consulta",
  "turn": 1,
  "is_final": true,
  "customer_phone": "+5511999999999",
  "customer_name": "João Silva"
}
```

**Resposta**:
```json
{
  "response": "Claro! Temos horários disponíveis para esta semana..."
}
```

**Fluxo**:
```
1. Recebe webhook do Retell
   ↓
2. Verifica is_final (processa apenas turnos completos)
   ↓
3. Busca ou cria Contact
   ↓
4. Busca ou cria Conversation (canal=retell_ai)
   ↓
5. Salva mensagem do cliente
   ↓
6. Processa com AgentEngine
   ↓
7. Salva resposta do agente
   ↓
8. Retorna texto para Retell converter em voz
```

#### POST /integrations/retell/call-ended/{tenant_id}

**Payload**:
```json
{
  "call_id": "abc123",
  "transcript": "Transcrição completa da ligação...",
  "duration_seconds": 180,
  "customer_phone": "+5511999999999",
  "recording_url": "https://..."
}
```

**Fluxo**:
```
1. Busca conversa pelo call_id
   ↓
2. Atualiza resumo com transcrição completa
   ↓
3. Marca status como CONCLUIDO
   ↓
4. Verifica se houve agendamento
   ├─ Não → Cria LeadRecovery (trigger=INATIVO, 24h)
   └─ Sim → Nada
```

## 💻 Uso

### Configurar Tenant para Áudio

```python
# Atualizar conexão WhatsApp
connection.modo_voz = "apenas_audio"
connection.elevenlabs_voice_id = "21m00Tcm4TlvDq8ikWAM"  # Rachel
await db.commit()
```

### Configurar Tenant para Retell AI

```python
connection.modo_voz = "retell"
connection.retell_agent_id = "agent_abc123"
await db.commit()

# Configurar webhook no Retell AI:
# URL: https://api.seudominio.com/integrations/retell/webhook/1/5
# (tenant_id=1, agent_id=5)
```

### Testar TTS

```bash
curl -X POST "https://api.seudominio.com/integrations/retell/test-tts/1" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Olá! Como posso ajudar você hoje?",
    "voice_id": "21m00Tcm4TlvDq8ikWAM"
  }'

# Resposta:
{
  "audio_url": "https://minio.../abc123.mp3",
  "cached": false,
  "duration_ms": 2500
}
```

## 🔄 Fluxo Completo: Resposta em Áudio

```
1. Cliente envia áudio no WhatsApp
   ↓
2. Webhook recebe mensagem
   ↓
3. Worker processa:
   ├─ Transcreve áudio (Whisper)
   ├─ Processa com AgentEngine
   └─ Gera resposta em texto
   ↓
4. _should_respond_audio() → True
   (cliente enviou áudio)
   ↓
5. _send_audio_responses():
   ├─ Para cada resposta:
   │  ├─ Gera áudio via ElevenLabs
   │  ├─ Salva no MinIO (cache)
   │  ├─ Envia como mensagem de áudio
   │  └─ Delay entre mensagens
   ↓
6. detect_voice_preference():
   Marca preferencia_voz=true
```

## 🔄 Fluxo Completo: Ligação Retell AI

```
1. Retell AI faz ligação para paciente
   ↓
2. Paciente: "Quero agendar consulta"
   ↓
3. Retell envia webhook (turn 1, is_final=true)
   POST /integrations/retell/webhook/1/5
   ↓
4. Nossa API:
   ├─ Busca/cria Contact
   ├─ Busca/cria Conversation
   ├─ Salva mensagem do cliente
   ├─ Processa com AgentEngine
   ├─ Salva resposta do agente
   └─ Retorna: {"response": "Claro! Temos..."}
   ↓
5. Retell converte resposta para voz
   ↓
6. Paciente ouve resposta
   ↓
7. Conversa continua... (turnos 2, 3, 4...)
   ↓
8. Ligação termina
   ↓
9. Retell envia webhook de fim
   POST /integrations/retell/call-ended/1
   ↓
10. Nossa API:
    ├─ Salva transcrição completa
    ├─ Marca conversa como CONCLUIDO
    ├─ Verifica se agendou
    └─ Se não: cria LeadRecovery
```

## 📈 Vozes Disponíveis (ElevenLabs)

| Voice ID | Nome | Idioma | Características |
|----------|------|--------|-----------------|
| `21m00Tcm4TlvDq8ikWAM` | Rachel | EN-US | Feminina, profissional |
| `AZnzlk1XvdvUeBnXmlld` | Domi | EN-US | Feminina, jovem |
| `EXAVITQu4vr4xnSDxMaL` | Bella | EN-US | Feminina, suave |
| `ErXwobaYiN019PkySvjV` | Antoni | EN-US | Masculina, profunda |
| `VR6AewLTigWG4xSOukaG` | Arnold | EN-US | Masculina, forte |
| `pNInz6obpgDQGcFmaJgB` | Adam | EN-US | Masculina, natural |

**Português**: Use modelo `eleven_multilingual_v2` para melhor qualidade em PT-BR.

## ⚙️ Variáveis de Ambiente

```env
# ElevenLabs
ELEVENLABS_API_KEY=sk_...

# Retell AI
RETELL_API_KEY=key_...

# MinIO
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_SECURE=false
```

## 🚀 Próximos Passos

- [ ] Suporte a múltiplas vozes por tenant
- [ ] Análise de sentimento em ligações
- [ ] Gravação de ligações no MinIO
- [ ] Dashboard de analytics de voz
- [ ] Integração com Twilio para ligações diretas
- [ ] Suporte a SSML para controle fino de prosódia
- [ ] Clonagem de voz personalizada por clínica

## 📚 Referências

- [ElevenLabs API](https://elevenlabs.io/docs/api-reference/text-to-speech)
- [Retell AI Documentation](https://docs.retellai.com/)
- [MinIO Python SDK](https://min.io/docs/minio/linux/developers/python/minio-py.html)
