# 🔄 Sistema de Recuperação de Leads - Documentação

## Visão Geral

Sistema inteligente de recuperação automática de leads inativos, com mensagens personalizadas via LLM, sequências específicas por tipo de trigger e escalonamento automático para atendimento humano.

## 🎯 Funcionalidades

### Triggers de Recuperação

Um lead entra no fluxo de recuperação quando:

✅ **INATIVO**: Iniciou conversa mas não agendou (inativo há X horas - configurável, padrão 4h)  
✅ **FALTOU**: Tinha consulta agendada e faltou (status "faltou")  
✅ **CANCELOU**: Cancelou agendamento sem reagendar  
✅ **ORÇAMENTO**: Recebeu proposta/orçamento mas não respondeu (inativo há 24h)

### Sequências de Recuperação

Cada trigger tem sua própria sequência de mensagens e intervalos:

**INATIVO (não agendou)**:
- Tentativa 1 (após 4h): Acompanhamento suave
- Tentativa 2 (após 24h): Benefício/urgência + horário específico
- Tentativa 3 (após 72h): Última tentativa + escalação para humano

**FALTOU À CONSULTA**:
- Tentativa 1 (após 2h): Verificar se está bem + reagendamento
- Tentativa 2 (após 24h): Desconto ou horário especial
- Tentativa 3 (após 72h): Encerrar com porta aberta

**CANCELOU**:
- Tentativa 1 (após 1h): Entender motivo + contornar objeção
- Tentativa 2 (após 48h): Alternativa (outro horário/médico)

**ORÇAMENTO**:
- Tentativa 1 (após 24h): Esclarecer dúvidas + facilitar decisão
- Tentativa 2 (após 72h): Última oportunidade + condições especiais

### Geração de Mensagens via LLM

Cada mensagem é **gerada dinamicamente** pelo GPT-4o com contexto completo:
- Histórico da conversa anterior
- Informações do procedimento de interesse
- Tentativa atual (evita repetir abordagem)
- Instruções: empático, não insistente, saída digna

## 📊 Modelo de Dados

### LeadRecovery

```python
class LeadRecovery(Base):
    """Recuperação de Leads"""
    
    # Relacionamentos
    tenant_id: int
    contact_id: int
    conversation_id: int (opcional)
    
    # Tipo de trigger
    trigger_tipo: LeadRecoveryTrigger  # inativo, faltou, cancelou, orcamento
    
    # Status
    status: LeadRecoveryStatus  # pendente, em_andamento, recuperado, desistiu
    
    # Controle de tentativas
    tentativa_atual: int
    max_tentativas: int  # Padrão: 3
    
    # Agendamento
    proxima_tentativa_em: DateTime
```

### Enums

```python
class LeadRecoveryTrigger(Enum):
    INATIVO = "inativo"
    FALTOU = "faltou"
    CANCELOU = "cancelou"
    ORCAMENTO = "orcamento"

class LeadRecoveryStatus(Enum):
    PENDENTE = "pendente"
    EM_ANDAMENTO = "em_andamento"
    RECUPERADO = "recuperado"
    DESISTIU = "desistiu"
```

## ⚙️ Workers Celery

### verificar_recuperacao_leads

**Frequência**: A cada 30 minutos

```python
@celery_app.task
def verificar_recuperacao_leads():
    """
    1. Busca leads com proxima_tentativa_em <= agora
    2. Para cada lead: gera mensagem via LLM
    3. Envia mensagem via WhatsApp
    4. Incrementa tentativa e agenda próxima
    5. Se atingiu max_tentativas: marca como desistiu e escala
    """
```

## 🤖 Geração de Mensagens via LLM

### Contexto Fornecido ao LLM

```python
context = f"""
Você está fazendo recuperação de lead para a clínica {tenant.nome}.

INFORMAÇÕES DO PACIENTE:
- Nome: {contact.nome}
- Telefone: {contact.telefone}

SITUAÇÃO:
- Trigger: {trigger_tipo}
- Tentativa: {tentativa_atual} de {max_tentativas}

HISTÓRICO DA CONVERSA ANTERIOR:
{historico_formatado}

{prompt_especifico_do_trigger}

INSTRUÇÕES IMPORTANTES:
- Seja empático e não insistente
- Não repita a mesma abordagem de tentativas anteriores
- Sempre dê uma saída digna ao paciente
- Mantenha tom profissional mas humanizado
- Máximo 150 caracteres por mensagem
"""
```

### Prompts Configuráveis

Cada tenant pode personalizar os prompts em `configuracoes`:

```json
{
  "prompts_recuperacao": {
    "inativo_tentativa_1": "Faça um acompanhamento suave...",
    "inativo_tentativa_2": "Destaque benefício e urgência...",
    "faltou_tentativa_1": "Demonstre preocupação genuína...",
    "cancelou_tentativa_1": "Tente entender o motivo..."
  },
  "horas_inatividade_lead": 4
}
```

## 🔄 Detecção Automática

### No Worker de Mensagens

Quando uma mensagem chega:

```python
# 1. Se cliente respondeu: cancelar recuperação ativa
await cancelar_lead_recovery(db, contact.id)

# 2. Verificar se conversa está inativa sem agendamento
await _verificar_lead_inativo(db, conversation, contact, tenant_id)
```

### Lógica de Detecção

```python
async def _verificar_lead_inativo():
    # Buscar configuração de tempo
    horas_inatividade = tenant.configuracoes.get("horas_inatividade_lead", 4)
    
    # Verificar se tem agendamento
    has_appointment = await db.execute(...)
    
    if has_appointment:
        return  # Não é lead inativo
    
    # Verificar tempo desde criação
    tempo_decorrido = now - conversation.created_at
    
    if tempo_decorrido > horas_inatividade:
        # Criar lead recovery
        await criar_lead_recovery(...)
```

### Trigger Automático: Faltou

No worker `verificar_ausencias`:

```python
for appointment in appointments_passados:
    appointment.status = AppointmentStatus.FALTOU
    
    # Criar lead recovery automaticamente
    await criar_lead_recovery(
        trigger_tipo=LeadRecoveryTrigger.FALTOU,
        delay_hours=2  # Primeira tentativa em 2h
    )
```

## 💻 Uso

### Criar Lead Recovery Manualmente

```python
from app.workers.lead_recovery import criar_lead_recovery
from app.models.lead_recovery import LeadRecoveryTrigger

# Exemplo: Cliente recebeu orçamento
lead = await criar_lead_recovery(
    db=db,
    tenant_id=1,
    contact_id=123,
    conversation_id=456,
    trigger_tipo=LeadRecoveryTrigger.ORCAMENTO,
    delay_hours=24  # Primeira tentativa em 24h
)
```

### Cancelar Recovery (Cliente Respondeu)

```python
from app.workers.lead_recovery import cancelar_lead_recovery

# Cancela automaticamente quando cliente responde
cancelado = await cancelar_lead_recovery(db, contact_id=123)
# Retorna True se havia recovery ativa
```

## 🔄 Fluxo Completo

### Exemplo: Lead Inativo

```
1. Cliente inicia conversa às 10h
   "Oi, quero agendar consulta"
   ↓
2. Agente responde com opções
   Cliente não responde mais
   ↓
3. Após 4h (14h): Sistema detecta inatividade
   Cria LeadRecovery (trigger=INATIVO, tentativa=0)
   proxima_tentativa_em = 14h
   ↓
4. Worker verificar_recuperacao_leads (14h30)
   Encontra lead pronto
   ↓
5. Gera mensagem via LLM
   Contexto: histórico + tentativa 1 + prompt "acompanhamento suave"
   LLM: "Oi João! Vi que você estava interessado em agendar. 
         Posso te ajudar a encontrar um horário? 😊"
   ↓
6. Envia via WhatsApp
   Salva na conversa
   tentativa_atual = 1
   proxima_tentativa_em = agora + 24h
   ↓
7. Cliente NÃO responde
   ↓
8. Após 24h: Tentativa 2
   LLM gera nova mensagem (diferente da anterior)
   "Olá! Temos vagas limitadas para esta semana. 
    Que tal quarta às 14h? Confirmo pra você?"
   ↓
9. Cliente RESPONDE: "Pode ser!"
   ↓
10. Sistema detecta resposta
    cancelar_lead_recovery() → status = RECUPERADO
    Agente IA processa normalmente
```

### Exemplo: Faltou à Consulta

```
1. Paciente tinha consulta às 14h
   ↓
2. Worker verificar_ausencias (diário 10h)
   Detecta que passou das 14h e status = AGENDADO
   ↓
3. Atualiza status = FALTOU
   Cria LeadRecovery (trigger=FALTOU, delay=2h)
   ↓
4. Após 2h (16h): Tentativa 1
   LLM: "Oi Maria! Notamos que você não pôde vir hoje. 
         Está tudo bem? Gostaria de reagendar?"
   ↓
5. Cliente: "Desculpa, tive um imprevisto"
   ↓
6. Sistema: cancelar_lead_recovery() → RECUPERADO
   Agente IA: oferece novos horários
```

## 🛡️ Prevenção de Duplicatas

```python
# Ao criar lead recovery
existing = await db.execute(
    select(LeadRecovery).where(
        and_(
            LeadRecovery.contact_id == contact_id,
            LeadRecovery.status.in_([PENDENTE, EM_ANDAMENTO])
        )
    )
)

if existing:
    return existing  # Não cria duplicado
```

## 📊 Escalonamento Automático

Quando atinge `max_tentativas` sem sucesso:

```python
async def _finalizar_recuperacao(lead, sucesso=False):
    if not sucesso:
        lead.status = LeadRecoveryStatus.DESISTIU
        
        # Escalar para humano
        conversation.agente_ativo = False
        conversation.status = ConversationStatus.ASSUMIDO
        
        # Notificar via WebSocket
        await broadcast_to_tenant(tenant_id, {
            "event": "lead_escalado",
            "conversation_id": conversation.id,
            "trigger": lead.trigger_tipo.value,
            "tentativas": lead.tentativa_atual
        })
```

## 📈 Métricas

### Importantes para Monitorar

- Taxa de recuperação por trigger
- Tentativa média até recuperação
- Taxa de escalonamento
- Tempo médio de resposta após tentativa
- Conversão de leads recuperados em agendamentos

### Queries Úteis

```sql
-- Taxa de recuperação por trigger
SELECT 
    trigger_tipo,
    COUNT(*) as total,
    SUM(CASE WHEN status = 'recuperado' THEN 1 ELSE 0 END) as recuperados,
    ROUND(100.0 * SUM(CASE WHEN status = 'recuperado' THEN 1 ELSE 0 END) / COUNT(*), 2) as taxa
FROM lead_recoveries
GROUP BY trigger_tipo;

-- Tentativa média até recuperação
SELECT 
    trigger_tipo,
    AVG(tentativa_atual) as tentativa_media
FROM lead_recoveries
WHERE status = 'recuperado'
GROUP BY trigger_tipo;
```

## 🚀 Próximos Passos

- [ ] Dashboard de analytics de recuperação
- [ ] A/B testing de prompts
- [ ] Recuperação multi-canal (SMS, Email)
- [ ] Machine learning para otimizar timing
- [ ] Segmentação de leads por valor potencial
- [ ] Templates de voz para recuperação via áudio

## 📚 Referências

- [LangChain Documentation](https://python.langchain.com/docs/get_started/introduction)
- [OpenAI GPT-4o](https://platform.openai.com/docs/models/gpt-4o)
- [Celery Beat Scheduling](https://docs.celeryproject.org/en/stable/userguide/periodic-tasks.html)
