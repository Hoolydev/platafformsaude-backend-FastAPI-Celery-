# 🐳 Docker Deployment - Guia Completo

## Visão Geral

Deploy completo da plataforma usando Docker Compose, otimizado para Coolify com serviços externos (Supabase, Redis, Evolution API).

## 📦 Serviços Incluídos

### 1. Backend (FastAPI)
- **Porta**: 8000
- **Workers**: 4 (uvicorn)
- **Healthcheck**: `/health`
- **Restart**: unless-stopped

### 2. Celery Worker
- **Concurrency**: 4 workers
- **Comando**: `celery -A app.workers.celery_app worker`
- **Healthcheck**: `celery inspect ping`

### 3. Celery Beat (Scheduler)
- **Comando**: `celery -A app.workers.celery_app beat`
- **Função**: Agendar tarefas periódicas (lembretes, recuperação de leads)

### 4. Flower (Monitoring)
- **Porta**: 5555
- **Função**: Dashboard de monitoramento do Celery
- **URL**: `http://localhost:5555`

### 5. MinIO (Storage)
- **Portas**: 9000 (API), 9001 (Console)
- **Volume**: `minio_data` (persistente)
- **Bucket**: Criado automaticamente via `minio_init`

### 6. MinIO Init
- **Função**: Criar bucket inicial
- **Executa**: Uma vez, após MinIO estar healthy
- **Bucket**: Nome definido em `MINIO_BUCKET_NAME`

## 🚀 Deploy no Coolify

### 1. Configurar Repositório Git

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/seu-usuario/seu-repo.git
git push -u origin main
```

### 2. Criar Projeto no Coolify

1. Acesse o Coolify
2. Clique em "New Resource" → "Git Repository"
3. Cole a URL do repositório
4. Selecione a branch `main`

### 3. Configurar Variáveis de Ambiente

No Coolify, vá em "Environment Variables" e adicione:

```env
DATABASE_URL=postgresql+asyncpg://...
SUPABASE_URL=https://...
SUPABASE_KEY=...
REDIS_URL=redis://...
CELERY_BROKER_URL=redis://...
CELERY_RESULT_BACKEND=redis://...
EVOLUTION_API_URL=https://...
EVOLUTION_API_KEY=...
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
ELEVENLABS_API_KEY=...
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123
MINIO_BUCKET_NAME=saude-platform
JWT_SECRET=...
JWT_ALGORITHM=HS256
```

### 4. Deploy

1. Clique em "Deploy"
2. Coolify detectará o `docker-compose.yml`
3. Aguarde o build e deploy

## 🔧 Desenvolvimento Local

### 1. Copiar .env.example

```bash
cp .env.example .env
```

### 2. Preencher Variáveis

Edite `.env` com suas credenciais.

### 3. Subir Serviços

```bash
docker-compose up -d
```

### 4. Ver Logs

```bash
# Todos os serviços
docker-compose logs -f

# Apenas backend
docker-compose logs -f backend

# Apenas celery worker
docker-compose logs -f celery_worker
```

### 5. Parar Serviços

```bash
docker-compose down
```

### 6. Rebuild

```bash
docker-compose up -d --build
```

## 📊 Monitoramento

### Flower (Celery)

Acesse: `http://localhost:5555`

**Features**:
- Workers ativos
- Tarefas em execução
- Histórico de tarefas
- Estatísticas

### MinIO Console

Acesse: `http://localhost:9001`

**Credenciais**:
- User: `MINIO_ACCESS_KEY`
- Password: `MINIO_SECRET_KEY`

**Features**:
- Gerenciar buckets
- Upload/download de arquivos
- Configurar políticas de acesso

### Backend Health

```bash
curl http://localhost:8000/health
```

**Resposta**:
```json
{
  "status": "healthy",
  "service": "Sistema Deus da Saúde",
  "version": "1.0.0"
}
```

## 🔍 Troubleshooting

### Backend não inicia

```bash
# Ver logs
docker-compose logs backend

# Verificar variáveis de ambiente
docker-compose exec backend env | grep DATABASE_URL
```

### Celery Worker não conecta ao Redis

```bash
# Testar conexão Redis
docker-compose exec celery_worker python -c "import redis; r = redis.from_url('REDIS_URL'); print(r.ping())"
```

### MinIO bucket não criado

```bash
# Recriar bucket manualmente
docker-compose exec minio mc alias set myminio http://localhost:9000 ACCESS_KEY SECRET_KEY
docker-compose exec minio mc mb myminio/BUCKET_NAME
```

### Healthcheck falhando

```bash
# Testar healthcheck manualmente
docker-compose exec backend curl -f http://localhost:8000/health
```

## 📁 Estrutura de Arquivos

```
.
├── docker-compose.yml       # Orquestração de serviços
├── Dockerfile               # Build multi-stage
├── .dockerignore            # Arquivos ignorados no build
├── .env.example             # Template de variáveis
├── .env                     # Variáveis (não commitar!)
├── requirements.txt         # Dependências Python
├── app/
│   ├── main.py             # FastAPI app
│   ├── workers/
│   │   └── celery_app.py   # Celery config
│   └── api/
│       └── v1/
│           └── health.py   # Healthcheck endpoint
└── README.md
```

## 🔒 Segurança

### Variáveis Sensíveis

**NUNCA** commite `.env` no Git!

```bash
# .gitignore
.env
.env.local
```

### Secrets no Coolify

Use o gerenciador de secrets do Coolify para:
- `JWT_SECRET`
- `OPENAI_API_KEY`
- `DATABASE_URL`
- Outras credenciais

### Non-root User

O Dockerfile usa um usuário não-root (`appuser`) para segurança.

## 🚀 Otimizações

### Multi-stage Build

- **Stage 1 (builder)**: Instala dependências
- **Stage 2 (runtime)**: Copia apenas o necessário
- **Resultado**: Imagem ~50% menor

### Cache de Layers

```dockerfile
# Copiar requirements primeiro (cache)
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copiar código depois
COPY . .
```

### Healthchecks

Todos os serviços têm healthcheck configurado:
- **Backend**: `curl /health`
- **Celery Worker**: `celery inspect ping`
- **MinIO**: `curl /minio/health/live`

## 📈 Escalabilidade

### Aumentar Workers Celery

```yaml
celery_worker:
  command: celery -A app.workers.celery_app worker --concurrency=8
```

### Aumentar Workers Uvicorn

```yaml
backend:
  command: uvicorn app.main:app --workers 8
```

### Múltiplas Réplicas (Docker Swarm)

```bash
docker service scale saude-backend=3
```

## 🔄 CI/CD

### GitHub Actions

```yaml
name: Deploy to Coolify

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Trigger Coolify Deploy
        run: curl -X POST ${{ secrets.COOLIFY_WEBHOOK_URL }}
```

## 📚 Referências

- [Docker Compose](https://docs.docker.com/compose/)
- [Coolify](https://coolify.io/docs)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [Celery](https://docs.celeryq.dev/)
- [MinIO](https://min.io/docs/)
