# 🚀 Guia de Deploy - Sistema Deus da Saúde

## Pré-requisitos

- Docker e Docker Compose instalados
- Git (opcional, para versionamento)
- Acesso ao servidor/VPS ou Coolify

## 📋 Checklist Pré-Deploy

- [ ] Configurar todas as variáveis de ambiente no `.env`
- [ ] Alterar todas as senhas padrão
- [ ] Configurar chaves de API (OpenAI, Z-API, Helena CRM)
- [ ] Configurar SSL/HTTPS
- [ ] Revisar configurações de CORS
- [ ] Configurar backup automático do banco de dados

## 🔧 Configuração Inicial

### 1. Clonar/Copiar Projeto

```bash
# Se usando Git
git clone <seu-repositorio>
cd Sistema\ Deus\ da\ Saude

# Ou copiar arquivos manualmente para o servidor
```

### 2. Configurar Variáveis de Ambiente

```bash
# Copiar .env.example para .env
cp .env.example .env

# Editar .env
nano .env
```

**Variáveis CRÍTICAS para mudar:**

```bash
# Segurança
SECRET_KEY=<gerar-chave-aleatoria-longa>
JWT_SECRET_KEY=<gerar-chave-aleatoria-longa>

# Banco de Dados
POSTGRES_PASSWORD=<senha-forte-postgres>

# Redis
REDIS_PASSWORD=<senha-forte-redis>

# MinIO
MINIO_ROOT_PASSWORD=<senha-forte-minio>

# Flower
FLOWER_PASSWORD=<senha-forte-flower>

# APIs Externas
OPENAI_API_KEY=<sua-chave-openai>
ZAPI_INSTANCE_ID=<seu-instance-id>
ZAPI_TOKEN=<seu-token>
HELENA_API_KEY=<sua-chave-helena>
```

### 3. Gerar Chaves Secretas

```bash
# Gerar SECRET_KEY e JWT_SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## 🐳 Deploy com Docker Compose

### 1. Build e Start

```bash
# Build das imagens
docker-compose build

# Iniciar todos os serviços
docker-compose up -d

# Ver logs
docker-compose logs -f
```

### 2. Criar Migrations

```bash
# Entrar no container do backend
docker-compose exec backend bash

# Criar migration inicial
alembic revision --autogenerate -m "Initial migration"

# Aplicar migrations
alembic upgrade head

# Sair do container
exit
```

### 3. Criar Primeiro Tenant e Usuário Admin

```bash
# Entrar no container
docker-compose exec backend python

# No Python shell:
```

```python
import asyncio
from app.database import AsyncSessionLocal
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.auth.password import hash_password

async def create_initial_data():
    async with AsyncSessionLocal() as db:
        # Criar tenant
        tenant = Tenant(
            nome="Clínica Exemplo",
            subdominio="clinica1",
            plano="pro",
            ativo=True
        )
        db.add(tenant)
        await db.flush()
        
        # Criar usuário admin
        admin = User(
            tenant_id=tenant.id,
            nome="Administrador",
            email="admin@clinica1.com",
            senha_hash=hash_password("Admin@123"),
            role=UserRole.ADMIN,
            ativo=True
        )
        db.add(admin)
        
        await db.commit()
        print(f"✅ Tenant criado: {tenant.nome} (ID: {tenant.id})")
        print(f"✅ Admin criado: {admin.email}")
        print(f"   Senha: Admin@123")

asyncio.run(create_initial_data())
```

### 4. Testar API

```bash
# Health check
curl http://localhost:8000/health

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@clinica1.com",
    "senha": "Admin@123"
  }'
```

## 🌐 Deploy no Coolify

### 1. Preparar Arquivos

Certifique-se de que todos estes arquivos estão no repositório:

```
✅ docker-compose.yml
✅ Dockerfile
✅ .env (ou configurar no Coolify)
✅ requirements.txt
✅ alembic.ini
✅ app/ (todo o código)
✅ alembic/ (migrations)
```

### 2. Configurar no Coolify

1. Criar novo serviço
2. Selecionar "Docker Compose"
3. Conectar ao repositório Git ou fazer upload
4. Configurar variáveis de ambiente
5. Deploy!

### 3. Após Deploy

```bash
# SSH no servidor
ssh user@seu-servidor

# Navegar para diretório do Coolify
cd /data/coolify/services/<service-id>

# Executar migrations
docker-compose exec backend alembic upgrade head

# Criar dados iniciais (ver seção anterior)
```

## 🔒 Configurar SSL/HTTPS

### Opção 1: Coolify (Automático)

O Coolify gerencia SSL automaticamente com Let's Encrypt.

### Opção 2: Manual com Nginx

```bash
# Gerar certificado Let's Encrypt
certbot certonly --standalone -d seudominio.com

# Copiar certificados
cp /etc/letsencrypt/live/seudominio.com/fullchain.pem nginx/ssl/cert.pem
cp /etc/letsencrypt/live/seudominio.com/privkey.pem nginx/ssl/key.pem

# Reiniciar Nginx
docker-compose restart nginx
```

## 📊 Monitoramento

### Acessar Serviços

- **API Docs**: https://seudominio.com/docs
- **Flower (Celery)**: https://seudominio.com:5555
- **MinIO Console**: https://seudominio.com:9001

### Ver Logs

```bash
# Todos os serviços
docker-compose logs -f

# Serviço específico
docker-compose logs -f backend
docker-compose logs -f celery_worker
docker-compose logs -f postgres
```

### Monitorar Recursos

```bash
# Ver uso de recursos
docker stats

# Ver status dos containers
docker-compose ps
```

## 🔄 Atualizações

### Deploy de Nova Versão

```bash
# Pull do código
git pull origin main

# Rebuild e restart
docker-compose build backend
docker-compose up -d backend

# Aplicar migrations
docker-compose exec backend alembic upgrade head
```

### Rollback

```bash
# Reverter migration
docker-compose exec backend alembic downgrade -1

# Voltar para versão anterior do código
git checkout <commit-anterior>
docker-compose build backend
docker-compose up -d backend
```

## 💾 Backup

### Backup Manual do Banco

```bash
# Criar backup
docker-compose exec postgres pg_dump -U saude_user saude_platform > backup-$(date +%Y%m%d).sql

# Restaurar backup
cat backup-20260217.sql | docker-compose exec -T postgres psql -U saude_user saude_platform
```

### Backup Automático (Cron)

```bash
# Editar crontab
crontab -e

# Adicionar linha (backup diário às 2h)
0 2 * * * cd /caminho/projeto && docker-compose exec -T postgres pg_dump -U saude_user saude_platform > backups/backup-$(date +\%Y\%m\%d).sql
```

## 🐛 Troubleshooting

### Backend não inicia

```bash
# Ver logs
docker-compose logs backend

# Verificar variáveis de ambiente
docker-compose exec backend env | grep DATABASE_URL

# Testar conexão com banco
docker-compose exec backend python -c "from app.database import engine; import asyncio; asyncio.run(engine.connect())"
```

### Migrations falham

```bash
# Ver histórico
docker-compose exec backend alembic history

# Ver status atual
docker-compose exec backend alembic current

# Forçar stamp (cuidado!)
docker-compose exec backend alembic stamp head
```

### Erro de permissão

```bash
# Ajustar permissões
sudo chown -R 1000:1000 .
```

## 📈 Performance

### Otimizações Recomendadas

1. **Banco de Dados**:
   - Criar índices nas colunas mais consultadas
   - Configurar connection pooling
   - Habilitar query caching

2. **Redis**:
   - Configurar eviction policy adequada
   - Monitorar uso de memória

3. **Backend**:
   - Aumentar workers do Uvicorn em produção
   - Configurar Gunicorn como process manager

4. **Celery**:
   - Ajustar concurrency dos workers
   - Monitorar fila de tarefas

## 🎯 Checklist Pós-Deploy

- [ ] API respondendo corretamente
- [ ] Autenticação funcionando
- [ ] Migrations aplicadas
- [ ] Dados iniciais criados
- [ ] SSL/HTTPS configurado
- [ ] Backup automático configurado
- [ ] Monitoramento ativo
- [ ] Logs sendo coletados
- [ ] Documentação atualizada
- [ ] Equipe treinada

## 📞 Suporte

Em caso de problemas:

1. Verificar logs: `docker-compose logs -f`
2. Verificar status: `docker-compose ps`
3. Verificar recursos: `docker stats`
4. Consultar documentação: `/docs`

---

**Boa sorte com o deploy! 🚀**
