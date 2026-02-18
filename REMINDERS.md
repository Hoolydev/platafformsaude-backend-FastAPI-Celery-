# 📅 Sistema de Lembretes Automáticos - Documentação

## Visão Geral

Sistema completo de lembretes automáticos para agendamentos de consultas, com envio via WhatsApp em 3 momentos estratégicos e processamento inteligente de respostas.

## 🎯 Funcionalidades

### Lembretes Automáticos

✅ **Confirmação Imediata**: Enviada logo após criar o agendamento  
✅ **Lembrete 24h**: Enviado 24 horas antes da consulta (±10min)  
✅ **Lembrete 2h**: Enviado 2 horas antes da consulta (±5min)  
✅ **Verificação de Ausências**: Marca como "faltou" consultas passadas sem confirmação

### Processamento de Respostas

✅ **SIM**: Confirma agendamento automaticamente  
✅ **NÃO**: Cancela e oferece reagendamento  
✅ **Outras**: Passa para o agente IA processar normalmente

### Templates Configuráveis

Cada tenant pode personalizar as mensagens nos seus `configuracoes` (JSONB).

## 📊 Modelos de Dados

### Appointment

```python
class Appointment(Base):
    """Agendamentos de consultas/procedimentos"""
    
    # Relacionamentos
    tenant_id: int
    contact_id: int
    procedure_id: int
    
    # Dados do agendamento
    data_hora: DateTime
    duracao_minutos: int = 30
    
    # Integração com calendários
    id_evento_calendar: str  # Google Calendar / Feegow event ID
    
    # Status
    status: AppointmentStatus  # agendado, confirmado, cancelado, realizado, faltou
    
    # Observações
    observacoes: str
```

### ReminderLog

```python
class ReminderLog(Base):
    """Log de lembretes enviados"""
    
    appointment_id: int
    tipo_lembrete: ReminderType  # confirmacao, lembrete_24h, lembrete_2h
    status: ReminderStatus  # enviado, erro, pendente
    enviado_em: DateTime
    erro: str
```

## ⚙️ Workers Celery

### verificar_lembretes_24h

**Frequência**: A cada hora  
**Janela**: 24h ±10min

```python
@celery_app.task
def verificar_lembretes_24h():
    """Busca agendamentos em 24h e envia lembrete"""
```

### verificar_lembretes_2h

**Frequência**: A cada 15 minutos  
**Janela**: 2h ±5min

```python
@celery_app.task
def verificar_lembretes_2h():
    """Busca agendamentos em 2h e envia lembrete"""
```

### verificar_ausencias

**Frequência**: Diariamente às 10h

```python
@celery_app.task
def verificar_ausencias():
    """Marca como 'faltou' consultas passadas sem confirmação"""
```

### enviar_confirmacao_imediata

**Trigger**: Chamado ao criar agendamento

```python
@celery_app.task
def enviar_confirmacao_imediata(appointment_id: int):
    """Envia confirmação imediata após agendamento"""
```

## 📝 Templates de Mensagem

### Configuração no Tenant

```json
{
  "configuracoes": {
    "lembrete_confirmacao": "Agendamento confirmado! ✅ {procedimento} em {data} às {hora}.",
    "lembrete_24h": "Olá {nome}! 👋 Lembrando que você tem {procedimento} amanhã às {hora}. Confirme com SIM ou cancele com NÃO.",
    "lembrete_2h": "Olá {nome}! Sua consulta é em 2 horas ({hora}). Estamos te esperando! 🏥",
    "endereco": "Rua Exemplo, 123 - São Paulo/SP",
    "link_maps": "https://maps.google.com/?q=..."
  }
}
```

### Placeholders Disponíveis

| Placeholder | Descrição |
|-------------|-----------|
| `{nome}` | Nome do paciente |
| `{procedimento}` | Nome do procedimento |
| `{data}` | Data formatada (dd/mm/yyyy) |
| `{hora}` | Hora formatada (HH:MM) |
| `{endereco}` | Endereço da clínica |
| `{link}` | Link do Google Maps |

## 💻 Uso

### 1. Criar Agendamento

```python
from app.models.appointment import Appointment, AppointmentStatus
from app.workers.reminders import enviar_confirmacao_imediata
from datetime import datetime, timedelta

# Criar agendamento
appointment = Appointment(
    tenant_id=1,
    contact_id=123,
    procedure_id=5,
    data_hora=datetime.now() + timedelta(days=2, hours=14),  # Daqui 2 dias às 14h
    duracao_minutos=30,
    status=AppointmentStatus.AGENDADO,
    observacoes="Primeira consulta"
)
db.add(appointment)
await db.commit()

# Enviar confirmação imediata
enviar_confirmacao_imediata.delay(appointment.id)
```

### 2. Processar Resposta

O processamento de respostas é automático quando uma mensagem chega:

```python
# No worker principal (app/workers.py)
# Verifica se é resposta a lembrete antes de processar com agente
is_reminder_response = await processar_resposta_lembrete(
    db, tenant_id, contact.id, message_text
)

if is_reminder_response:
    # Já foi processado (confirmado ou cancelado)
    return
```

## 🔄 Fluxo Completo

### Criação de Agendamento

```
1. API cria Appointment
   ↓
2. Trigger: enviar_confirmacao_imediata
   ↓
3. Busca template "lembrete_confirmacao"
   ↓
4. Personaliza com dados do agendamento
   ↓
5. Envia via WhatsApp
   ↓
6. Salva ReminderLog (tipo=confirmacao, status=enviado)
   ↓
7. Salva na memória do agente (tabela messages)
```

### Lembrete 24h Antes

```
Celery Beat (a cada hora)
   ↓
verificar_lembretes_24h
   ↓
Busca agendamentos em 24h ±10min
   ↓
Para cada agendamento:
   ├─ Verifica se já enviou (ReminderLog)
   ├─ Busca template "lembrete_24h"
   ├─ Personaliza mensagem
   ├─ Envia via WhatsApp
   ├─ Salva ReminderLog
   └─ Salva na memória do agente
```

### Resposta do Paciente

```
Paciente responde "SIM"
   ↓
Webhook recebe mensagem
   ↓
Worker processa
   ↓
processar_resposta_lembrete()
   ├─ Detecta "SIM"
   ├─ Busca último agendamento futuro
   ├─ Atualiza status para CONFIRMADO
   ├─ Envia confirmação
   └─ Retorna True (já processado)
```

## 📋 Exemplo Prático

### Cenário: Consulta Cardiologia

```python
# 1. Criar agendamento
appointment = Appointment(
    tenant_id=1,
    contact_id=456,  # João Silva
    procedure_id=10,  # Consulta Cardiologia
    data_hora=datetime(2026, 2, 20, 14, 0),  # 20/02/2026 às 14:00
    duracao_minutos=30,
    status=AppointmentStatus.AGENDADO
)

# 2. Confirmação imediata (enviada agora)
# "Agendamento confirmado! ✅ Consulta Cardiologia em 20/02/2026 às 14:00."

# 3. Lembrete 24h (enviado em 19/02/2026 às 14:00)
# "Olá João Silva! 👋 Lembrando que você tem Consulta Cardiologia amanhã às 14:00. 
#  Confirme com SIM ou cancele com NÃO."

# 4. Paciente responde "SIM" (19/02/2026 às 15:30)
# Sistema: Atualiza status para CONFIRMADO
# Resposta: "✅ Agendamento confirmado! Obrigado. Te esperamos no horário marcado."

# 5. Lembrete 2h (enviado em 20/02/2026 às 12:00)
# "Olá João Silva! Sua consulta é em 2 horas (14:00). Estamos te esperando! 🏥"

# 6. Consulta realizada (20/02/2026 às 14:00)
# Status manualmente atualizado para REALIZADO
```

## 🛡️ Prevenção de Duplicatas

O sistema verifica `ReminderLog` antes de enviar:

```python
# Buscar se já foi enviado
result = await db.execute(
    select(ReminderLog).where(
        and_(
            ReminderLog.appointment_id == appointment.id,
            ReminderLog.tipo_lembrete == tipo_lembrete,
            ReminderLog.status == ReminderStatus.ENVIADO
        )
    )
)
existing_log = result.scalar_one_or_none()

if existing_log:
    print("Lembrete já enviado")
    return
```

## 📊 Monitoramento

### Métricas Importantes

- Taxa de confirmação (respostas "SIM")
- Taxa de cancelamento (respostas "NÃO")
- Taxa de ausências (status "faltou")
- Tempo médio de resposta ao lembrete

### Logs

```bash
# Ver lembretes enviados
docker-compose logs -f celery_worker | grep "Lembrete"

# Ver verificações
docker-compose logs -f celery_worker | grep "Encontrados"

# Ver ausências
docker-compose logs -f celery_worker | grep "faltou"
```

## 🚀 Próximos Passos

- [ ] Fluxo de reagendamento automático
- [ ] Pesquisa de satisfação pós-consulta
- [ ] Lembretes de retorno (follow-up médico)
- [ ] Integração com Google Calendar para sincronização bidirecional
- [ ] Dashboard de analytics de lembretes
- [ ] Suporte a múltiplos canais (SMS, Email)
- [ ] A/B testing de templates de mensagem
- [ ] Lembretes personalizados por tipo de procedimento

## 📚 Referências

- [Celery Beat Documentation](https://docs.celeryproject.org/en/stable/userguide/periodic-tasks.html)
- [SQLAlchemy Relationships](https://docs.sqlalchemy.org/en/20/orm/relationships.html)
- [WhatsApp Business API](https://developers.facebook.com/docs/whatsapp)
