# 📊 Dashboard e Métricas - Documentação

## Visão Geral

Sistema completo de dashboard analytics com endpoints FastAPI e interface Next.js com gráficos interativos.

## 🎯 Endpoints de Métricas (Backend)

### GET /api/v1/metrics/overview

**Parâmetros**:
- `periodo`: `hoje`, `7d`, `30d`, `90d`

**Resposta**:
```json
{
  "total_conversas": 150,
  "conversas_ativas": 12,
  "conversas_concluidas": 138,
  "total_agendamentos": 85,
  "agendamentos_confirmados": 72,
  "taxa_confirmacao": 84.7,
  "leads_recuperados": 23,
  "taxa_recuperacao": 45.1,
  "tempo_medio_resposta_segundos": 12.5,
  "mensagens_enviadas_agente": 450,
  "mensagens_enviadas_humano": 28
}
```

### GET /api/v1/metrics/conversations-by-day

**Parâmetros**:
- `periodo`: `7d`, `30d`, `90d`

**Resposta**:
```json
[
  {
    "data": "2026-02-17",
    "total": 15,
    "agendadas": 8,
    "canceladas": 2,
    "faltaram": 1
  }
]
```

### GET /api/v1/metrics/top-procedures

**Parâmetros**:
- `limit`: número de procedimentos (padrão: 10)

**Resposta**:
```json
[
  {
    "id": 1,
    "nome": "Consulta Cardiologia",
    "total_agendamentos": 45
  }
]
```

### GET /api/v1/metrics/agent-performance

**Parâmetros**:
- `periodo`: `7d`, `30d`

**Resposta**:
```json
{
  "taxa_escalacao": 8.5,
  "taxa_agendamento": 56.7,
  "tempo_medio_resolucao_minutos": 15.3
}
```

## 🎨 Dashboard Frontend (Next.js)

### Estrutura

```
frontend/
├── app/
│   ├── [tenant]/
│   │   └── dashboard/
│   │       └── page.tsx          # Página principal
│   ├── layout.tsx                # Layout com React Query
│   └── globals.css               # Estilos globais
├── components/
│   └── ui/
│       └── card.tsx              # Componente Card (shadcn/ui)
├── lib/
│   ├── api.ts                    # Cliente API
│   └── utils.ts                  # Utilitários
├── package.json
├── tailwind.config.ts
└── tsconfig.json
```

### Componentes Principais

#### 1. Cards de Resumo

```tsx
<MetricCard
  title="Conversas"
  value={150}
  subtitle="12 ativas"
  icon={<Users />}
  trend={5.2}
/>
```

**Features**:
- Valor principal com formatação
- Subtítulo descritivo
- Ícone temático (lucide-react)
- Indicador de tendência (↑/↓)
- Skeleton loading

#### 2. Gráfico de Linha (Conversas por Dia)

```tsx
<LineChart data={conversationsByDay}>
  <Line dataKey="total" stroke="#3b82f6" />
  <Line dataKey="agendadas" stroke="#10b981" />
</LineChart>
```

**Features**:
- Recharts responsivo
- Tooltip com formatação de data
- Múltiplas linhas (total, agendadas)
- Grid e eixos customizados

#### 3. Gráfico de Barras (Top Procedimentos)

```tsx
<BarChart data={topProcedures} layout="vertical">
  <Bar dataKey="total_agendamentos" fill="#3b82f6" />
</BarChart>
```

**Features**:
- Layout horizontal
- Top 10 procedimentos
- Tooltip interativo

### Filtros de Período

```tsx
const periodos = ['hoje', '7d', '30d', '90d'];

<button onClick={() => setPeriodo('7d')}>
  7 dias
</button>
```

**Comportamento**:
- Botões com estado ativo
- Atualiza todas as queries automaticamente
- Cache de 5 minutos por período

### React Query

```tsx
const { data, isLoading } = useQuery({
  queryKey: ['metrics-overview', periodo],
  queryFn: () => metricsAPI.getOverview(periodo),
  staleTime: 5 * 60 * 1000, // 5 minutos
});
```

**Configuração**:
- Cache de 5 minutos
- Refetch desabilitado no focus
- Skeleton loading durante fetch

## 🚀 Como Usar

### Backend

1. **Registrar rotas**:

```python
# app/main.py
from app.api.v1.metrics import router as metrics_router

app.include_router(metrics_router, prefix="/api/v1")
```

2. **Testar endpoints**:

```bash
curl "http://localhost:8000/api/v1/metrics/overview?periodo=7d" \
  -H "Authorization: Bearer TOKEN"
```

### Frontend

1. **Instalar dependências**:

```bash
cd frontend
npm install
```

2. **Configurar variáveis de ambiente**:

```env
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

3. **Rodar dev server**:

```bash
npm run dev
```

4. **Acessar dashboard**:

```
http://localhost:3000/[tenant]/dashboard
```

## 📈 Métricas Disponíveis

### Overview
- **Total de conversas**: Todas as conversas no período
- **Conversas ativas**: Em andamento
- **Conversas concluídas**: Finalizadas
- **Total de agendamentos**: Criados no período
- **Taxa de confirmação**: % de agendamentos confirmados
- **Leads recuperados**: Recuperações bem-sucedidas
- **Taxa de recuperação**: % de leads recuperados
- **Tempo médio de resposta**: Em segundos
- **Mensagens por origem**: Agente vs Humano

### Performance do Agente
- **Taxa de escalação**: % de conversas transferidas para humano
- **Taxa de agendamento**: % de conversas que resultaram em agendamento
- **Tempo médio de resolução**: Em minutos

### Conversas por Dia
- Total de conversas
- Conversas com agendamento
- Agendamentos cancelados
- Pacientes que faltaram

### Top Procedimentos
- Procedimentos mais agendados
- Contagem de agendamentos

## 🎨 Customização

### Cores do Tema

```css
/* globals.css */
:root {
  --primary: 221.2 83.2% 53.3%;      /* Azul */
  --secondary: 210 40% 96.1%;        /* Cinza claro */
  --destructive: 0 84.2% 60.2%;      /* Vermelho */
}
```

### Adicionar Nova Métrica

1. **Backend**:

```python
@router.get("/new-metric")
async def get_new_metric(
    tenant_id: int = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    # Query
    result = await db.execute(...)
    return {"value": result.scalar()}
```

2. **Frontend**:

```tsx
// lib/api.ts
export const metricsAPI = {
  getNewMetric: (token?: string) =>
    fetchAPI<number>('/metrics/new-metric', token),
};

// page.tsx
const { data } = useQuery({
  queryKey: ['new-metric'],
  queryFn: () => metricsAPI.getNewMetric(),
});
```

## 🔒 Autenticação

Todos os endpoints requerem autenticação via `get_current_tenant`:

```python
tenant_id: int = Depends(get_current_tenant)
```

No frontend, passar token no header:

```typescript
headers: {
  'Authorization': `Bearer ${token}`
}
```

## 📱 Responsividade

O dashboard é totalmente responsivo:

```tsx
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
  {/* Cards se adaptam ao tamanho da tela */}
</div>
```

**Breakpoints**:
- Mobile: 1 coluna
- Tablet (md): 2 colunas
- Desktop (lg): 4 colunas

## 🚀 Próximos Passos

- [ ] Exportar relatórios em PDF
- [ ] Filtro por agente específico
- [ ] Comparação entre períodos
- [ ] Alertas de métricas críticas
- [ ] Dashboard em tempo real (WebSocket)
- [ ] Gráficos de funil de conversão
- [ ] Heatmap de horários de pico
