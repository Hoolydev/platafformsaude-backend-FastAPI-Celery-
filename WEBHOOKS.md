# 📱 Sistema de Webhooks WhatsApp - Documentação

## Visão Geral

Sistema completo de webhooks para receber e enviar mensagens WhatsApp com suporte a múltiplos providers:
- **Z-API**
- **UazAPI**
- **WhatsApp Business API Oficial (Meta)**

## 🎯 Funcionalidades

### Recebimento de Mensagens (Inbound)

✅ **Endpoints separados por provider**:
```
POST /api/v1/webhooks/zapi/{tenant_id}/{connection_id}
POST /api/v1/webhooks/uazapi/{tenant_id}/{connection_id}
POST /api/v1/webhooks/oficial/{tenant_id}/{connection_id}
GET  /api/v1/webhooks/oficial/{tenant_id}/{connection_id}  # Verificação Meta
```

✅ **Validação de assinaturas**:
- Z-API: HMAC SHA256
- UazAPI: Bearer token
- Meta: X-Hub-Signature-256

✅ **Normalização automática** de mensagens para formato interno

✅ **Fila Redis** para processamento assíncrono

✅ **Worker Celery** para processar mensagens em background

### Envio de Mensagens (Outbound)

✅ **Classe `WhatsAppSender`** com detecção automática de provider

✅ **Retry automático** com exponential backoff (3 tentativas)

✅ **Suporte a múltiplos tipos**:
- Texto
- Imagem (URL ou base64)
- Áudio
- Documento
- Template (apenas Meta)

### Comunicação em Tempo Real

✅ **WebSocket** endpoint: `WS /api/v1/ws/{tenant_id}`

✅ **Eventos suportados**:
- `nova_mensagem`
- `conversa_atualizada`
- `agente_escalou`
- `digitando`
- `atendente_assumiu`

## 📦 Estrutura de Arquivos

```
app/
├── services/whatsapp/
│   ├── parsers.py          # Normalização de mensagens
│   └── sender.py           # Envio com retry
├── api/v1/
│   ├── webhooks.py         # Endpoints de recebimento
│   └── websocket.py        # WebSocket tempo real
└── workers.py              # Celery tasks
```

## 🔧 Configuração

### 1. Criar Conexão WhatsApp

```python
# Exemplo: Z-API
connection = WhatsappConnection(
    tenant_id=1,
    numero="5511999999999",
    provider=WhatsappProvider.ZAPI,
    credenciais={
        "instance_id": "SEU_INSTANCE_ID",
        "token": "SEU_TOKEN",
        "webhook_token": "TOKEN_PARA_VALIDACAO"  # Opcional
    },
    webhook_url="https://seudominio.com/api/v1/webhooks/zapi/1/1",
    ativo=True
)
```

```python
# Exemplo: UazAPI
connection = WhatsappConnection(
    tenant_id=1,
    numero="5511999999999",
    provider=WhatsappProvider.UAZAPI,
    credenciais={
        "api_key": "SUA_API_KEY",
        "instance_id": "SEU_INSTANCE_ID",
        "webhook_token": "TOKEN_PARA_VALIDACAO"
    },
    webhook_url="https://seudominio.com/api/v1/webhooks/uazapi/1/1",
    ativo=True
)
```

```python
# Exemplo: WhatsApp Business API Oficial (Meta)
connection = WhatsappConnection(
    tenant_id=1,
    numero="5511999999999",
    provider=WhatsappProvider.OFICIAL,
    credenciais={
        "access_token": "SEU_ACCESS_TOKEN",
        "phone_number_id": "SEU_PHONE_NUMBER_ID",
        "app_secret": "SEU_APP_SECRET",
        "verify_token": "TOKEN_DE_VERIFICACAO"
    },
    webhook_url="https://seudominio.com/api/v1/webhooks/oficial/1/1",
    ativo=True
)
```

### 2. Configurar Webhook no Provider

#### Z-API
1. Acesse o painel da Z-API
2. Configure webhook URL: `https://seudominio.com/api/v1/webhooks/zapi/{tenant_id}/{connection_id}`
3. Ative eventos de mensagens recebidas

#### UazAPI
1. Acesse o painel da UazAPI
2. Configure webhook URL: `https://seudominio.com/api/v1/webhooks/uazapi/{tenant_id}/{connection_id}`
3. Configure Bearer token no header

#### Meta (WhatsApp Business API)
1. Acesse o Meta App Dashboard
2. Configure webhook URL: `https://seudominio.com/api/v1/webhooks/oficial/{tenant_id}/{connection_id}`
3. Configure verify_token
4. Subscreva aos eventos: `messages`

## 💻 Uso

### Enviar Mensagem

```python
from app.services.whatsapp.sender import WhatsAppSender
from app.models.connection import WhatsappConnection

# Buscar conexão
connection = await db.get(WhatsappConnection, connection_id)

# Criar sender
sender = WhatsAppSender(connection)

# Enviar texto
await sender.send(
    phone="5511999999999",
    message_type="text",
    message="Olá! Como posso ajudar?"
)

# Enviar imagem
await sender.send(
    phone="5511999999999",
    message_type="image",
    image_url="https://example.com/image.jpg",
    caption="Confira nossa promoção!"
)

# Enviar áudio
await sender.send(
    phone="5511999999999",
    message_type="audio",
    audio_url="https://example.com/audio.ogg"
)

# Enviar documento
await sender.send(
    phone="5511999999999",
    message_type="document",
    document_url="https://example.com/doc.pdf",
    filename="catalogo.pdf"
)

# Enviar template (apenas Meta)
await sender.send(
    phone="5511999999999",
    message_type="template",
    template_name="hello_world",
    language="pt_BR"
)
```

### WebSocket (Frontend)

```javascript
// Conectar ao WebSocket
const token = "SEU_ACCESS_TOKEN";
const tenantId = 1;
const ws = new WebSocket(`ws://localhost:8000/api/v1/ws/${tenantId}?token=${token}`);

// Receber eventos
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    switch (data.event) {
        case 'connected':
            console.log('Conectado!', data);
            break;
        
        case 'nova_mensagem':
            console.log('Nova mensagem:', data);
            // Atualizar UI
            break;
        
        case 'conversa_atualizada':
            console.log('Conversa atualizada:', data);
            break;
        
        case 'digitando':
            console.log('Alguém está digitando:', data);
            break;
    }
};

// Enviar evento
ws.send(JSON.stringify({
    event: 'digitando',
    conversation_id: 123
}));

// Ping/Pong
setInterval(() => {
    ws.send(JSON.stringify({ event: 'ping' }));
}, 30000);
```

## 🔄 Fluxo de Processamento

### 1. Mensagem Recebida

```
WhatsApp → Webhook Endpoint → Validação → Parser → Fila Redis → Worker Celery
```

### 2. Worker Celery

```python
process_incoming_message(tenant_id, message_data):
    1. Buscar ou criar Contact
    2. Buscar ou criar Conversation
    3. Salvar Message no banco
    4. Verificar se agente está ativo
    5a. Se ativo: processar com agente IA → enviar respostas
    5b. Se não: notificar atendentes via WebSocket
```

### 3. Resposta do Agente IA

```
Worker → Agent Engine → LLM → Ferramentas → Resposta → WhatsAppSender → WhatsApp
```

## 📊 Tipos de Mensagem Suportados

| Tipo | Z-API | UazAPI | Meta | Descrição |
|------|-------|--------|------|-----------|
| text | ✅ | ✅ | ✅ | Mensagem de texto |
| image | ✅ | ✅ | ✅ | Imagem com caption |
| audio | ✅ | ✅ | ✅ | Áudio/voz |
| document | ✅ | ✅ | ✅ | PDF, DOC, etc |
| video | ✅ | ✅ | ✅ | Vídeo |
| sticker | ✅ | ✅ | ✅ | Figurinha |
| location | ✅ | ✅ | ✅ | Localização |
| template | ❌ | ❌ | ✅ | Template message |

## 🔒 Segurança

### Validação de Assinaturas

**Z-API**:
```python
signature = hmac.new(
    webhook_token.encode(),
    payload_bytes,
    hashlib.sha256
).hexdigest()
```

**Meta**:
```python
signature = "sha256=" + hmac.new(
    app_secret.encode(),
    payload_bytes,
    hashlib.sha256
).hexdigest()
```

**UazAPI**:
```
Authorization: Bearer {webhook_token}
```

### Recomendações

- ✅ Sempre validar assinaturas em produção
- ✅ Usar HTTPS para webhooks
- ✅ Rotacionar tokens periodicamente
- ✅ Monitorar tentativas de acesso não autorizado
- ✅ Rate limiting nos endpoints de webhook

## 🐛 Troubleshooting

### Webhook não recebe mensagens

1. Verificar se URL está acessível publicamente
2. Verificar se HTTPS está configurado
3. Verificar logs do provider
4. Testar endpoint manualmente com curl

### Mensagens não são processadas

1. Verificar se Celery worker está rodando
2. Verificar logs do worker: `docker-compose logs -f celery_worker`
3. Verificar fila Redis: `redis-cli LLEN queue:messages:1`
4. Verificar se conexão está ativa no banco

### WebSocket não conecta

1. Verificar se token JWT é válido
2. Verificar se tenant_id corresponde ao usuário
3. Verificar logs do backend
4. Testar com ferramenta como Postman

## 📈 Monitoramento

### Métricas Importantes

- Mensagens recebidas por minuto
- Tempo de processamento médio
- Taxa de erro de envio
- Conexões WebSocket ativas
- Tamanho da fila Redis

### Logs

```bash
# Ver logs do webhook
docker-compose logs -f backend | grep webhook

# Ver logs do worker
docker-compose logs -f celery_worker

# Ver fila Redis
docker-compose exec redis redis-cli
> LLEN queue:messages:1
> LRANGE queue:messages:1 0 10
```

## 🚀 Próximos Passos

- [ ] Implementar integração completa com OpenAI
- [ ] Adicionar suporte a mais providers (Twilio, etc)
- [ ] Implementar rate limiting por tenant
- [ ] Adicionar métricas com Prometheus
- [ ] Criar dashboard de monitoramento
- [ ] Implementar retry queue para mensagens falhadas
- [ ] Adicionar suporte a mensagens de template personalizadas
- [ ] Implementar cache de contatos/conversas

## 📚 Referências

- [Z-API Documentation](https://developer.z-api.io/)
- [WhatsApp Business API (Meta)](https://developers.facebook.com/docs/whatsapp)
- [Celery Documentation](https://docs.celeryproject.org/)
- [FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/)
