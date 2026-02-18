# 🎉 Backend FastAPI Multi-tenant - Sistema Deus da Saúde

Backend completo em Python com FastAPI para plataforma SaaS multi-tenant de saúde com agentes de IA.

## ✨ Funcionalidades

### Multi-tenancy
- ✅ Isolamento total de dados por tenant via `tenant_id`
- ✅ Detecção automática de tenant via subdomínio ou header `X-Tenant-ID`
- ✅ Middleware que injeta tenant em todas as requests

### Autenticação & Autorização
- ✅ JWT com access token e refresh token
- ✅ Password hashing com bcrypt
- ✅ Roles: admin, atendente, visualizador
- ✅ Endpoints: `/api/v1/auth/login`, `/api/v1/auth/refresh`, `/api/v1/auth/logout`

### Modelos de Dados
- ✅ **Tenant**: Clínicas/empresas com planos e configurações
- ✅ **User**: Usuários com roles e isolamento por tenant
- ✅ **Contact**: Contatos/pacientes com metadados flexíveis
- ✅ **Conversation**: Conversas com status (ativo/assumido/concluído)
- ✅ **Message**: Mensagens (texto/áudio/imagem/documento)
- ✅ **Agent**: Agentes de IA com instruções e configurações LLM
- ✅ **AgentTool**: Ferramentas dos agentes (agendar, cancelar, escalar, etc)
- ✅ **Procedure**: Procedimentos médicos com duração e valores
- ✅ **WhatsappConnection**: Integração WhatsApp (Z-API, oficial)
- ✅ **CalendarConnection**: Integração com agendas (Google, Feegow)

### API REST (v1)
- ✅ **Auth**: Login, refresh token, logout
- ✅ **Users**: CRUD completo com controle de acesso
- ✅ **Contacts**: CRUD de contatos/pacientes
- ✅ **Conversations**: CRUD + assumir/finalizar conversa
- ✅ **Agents**: CRUD de agentes IA + gerenciamento de ferramentas
- ✅ **Procedures**: CRUD de procedimentos
- ✅ **Webhooks**: Estrutura para WhatsApp e Calendar

## 📁 Estrutura do Projeto

```
backend/
├── app/
│   ├── main.py                 # FastAPI app principal
│   ├── database.py             # SQLAlchemy config (async)
│   ├── config.py               # Configurações centralizadas
│   ├── workers.py              # Celery workers
│   ├── auth/                   # Autenticação
│   │   ├── jwt.py              # JWT tokens
│   │   ├── password.py         # Password hashing
│   │   └── dependencies.py     # Auth dependencies
│   ├── middleware/             # Middlewares
│   │   └── tenant.py           # Multi-tenancy middleware
│   ├── models/                 # Modelos SQLAlchemy
│   │   ├── tenant.py
│   │   ├── user.py
│   │   ├── contact.py
│   │   ├── conversation.py
│   │   ├── message.py
│   │   ├── agent.py
│   │   ├── procedure.py
│   │   └── connection.py
│   ├── schemas/                # Schemas Pydantic v2
│   │   ├── auth.py
│   │   ├── tenant.py
│   │   ├── user.py
│   │   ├── contact.py
│   │   ├── conversation.py
│   │   ├── message.py
│   │   ├── agent.py
│   │   └── procedure.py
│   └── api/v1/                 # Endpoints REST
│       ├── auth.py
│       ├── users.py
│       ├── contacts.py
│       ├── conversations.py
│       ├── agents.py
│       ├── procedures.py
│       └── webhooks.py
├── alembic/                    # Migrations
│   ├── env.py
│   └── versions/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env
```

## 🚀 Como Usar

### 1. Configurar Ambiente

```bash
# Copiar .env.example para .env
cp .env.example .env

# Editar .env com suas configurações
nano .env
```

### 2. Iniciar Serviços

```bash
# Subir todos os serviços (backend, postgres, redis, etc)
docker-compose up -d

# Ver logs
docker-compose logs -f backend
```

### 3. Criar Migration Inicial

```bash
# Entrar no container
docker-compose exec backend bash

# Criar migration
alembic revision --autogenerate -m "Initial migration"

# Aplicar migration
alembic upgrade head
```

### 4. Acessar API

- **Documentação Swagger**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## 📝 Exemplos de Uso

### Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@clinica.com",
    "senha": "senha123"
  }'
```

### Criar Usuário (com token)

```bash
curl -X POST http://localhost:8000/api/v1/users \
  -H "Authorization: Bearer SEU_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "nome": "João Silva",
    "email": "joao@clinica.com",
    "senha": "senha123",
    "role": "atendente"
  }'
```

### Listar Contatos

```bash
curl -X GET http://localhost:8000/api/v1/contacts \
  -H "Authorization: Bearer SEU_ACCESS_TOKEN" \
  -H "X-Tenant-ID: 1"
```

## 🔧 Comandos Úteis

```bash
# Criar nova migration
docker-compose exec backend alembic revision --autogenerate -m "Descrição"

# Aplicar migrations
docker-compose exec backend alembic upgrade head

# Reverter migration
docker-compose exec backend alembic downgrade -1

# Ver histórico de migrations
docker-compose exec backend alembic history

# Acessar shell Python
docker-compose exec backend python

# Acessar banco de dados
docker-compose exec postgres psql -U saude_user saude_platform
```

## 🔐 Multi-tenancy

O sistema detecta o tenant de 3 formas (em ordem de prioridade):

1. **Header `X-Tenant-ID`**: 
   ```bash
   curl -H "X-Tenant-ID: 1" http://localhost:8000/api/v1/contacts
   ```

2. **Subdomínio**:
   ```
   http://clinica1.saudeplataform.com/api/v1/contacts
   ```

3. **Query parameter** (apenas desenvolvimento):
   ```
   http://localhost:8000/api/v1/contacts?tenant_id=1
   ```

## 🎯 Próximos Passos

- [ ] Implementar lógica de processamento de webhooks WhatsApp
- [ ] Integrar com OpenAI para agentes IA
- [ ] Implementar sistema de agendamento
- [ ] Adicionar testes unitários e de integração
- [ ] Implementar rate limiting
- [ ] Adicionar logging estruturado
- [ ] Criar seed data para desenvolvimento
- [ ] Documentar fluxos de integração

## 📚 Tecnologias

- **FastAPI** 0.109.0 - Framework web moderno e rápido
- **SQLAlchemy** 2.0.25 - ORM async
- **Alembic** 1.13.1 - Migrations
- **Pydantic** v2 - Validação de dados
- **PostgreSQL** 16 - Banco de dados
- **Redis** 7 - Cache e message broker
- **Celery** - Tarefas assíncronas
- **JWT** - Autenticação
- **Bcrypt** - Password hashing

## 📄 Licença

Proprietário - Todos os direitos reservados
