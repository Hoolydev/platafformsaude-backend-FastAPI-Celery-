# 🚀 Guia Rápido de Deploy no Coolify

## ⚠️ Problema que você está enfrentando

O erro `failed to read dockerfile: open Dockerfile: no such file or directory` acontece porque o Coolify precisa de **todos os arquivos** no diretório de deploy.

## ✅ Solução: Arquivos que você DEVE enviar para o Coolify

### 1. Arquivos Obrigatórios na Raiz
```
📁 Seu Projeto/
├── docker-compose.yml      ✅ Já criado
├── Dockerfile              ✅ Já criado
├── .env                    ✅ Já criado (MUDE AS SENHAS!)
├── .dockerignore           ✅ Já criado
├── requirements.txt        ✅ Já criado
└── app/                    ✅ Já criado
    ├── __init__.py
    ├── main.py
    ├── workers.py
    └── config.py
```

### 2. Arquivos Opcionais (mas recomendados)
```
├── nginx/
│   ├── nginx.conf
│   └── conf.d/
│       └── default.conf
└── scripts/
    ├── deploy.sh
    └── minio-init.sh
```

## 🔧 Passos para Deploy no Coolify

### Passo 1: Verifique o arquivo .env
Abra o arquivo `.env` e **MUDE TODAS AS SENHAS**:
```bash
POSTGRES_PASSWORD=SuaSenhaForteAqui123!
REDIS_PASSWORD=SuaSenhaRedis456!
MINIO_ROOT_PASSWORD=SuaSenhaMinio789!
FLOWER_PASSWORD=SuaSenhaFlower012!
SECRET_KEY=sua-chave-secreta-aleatoria-muito-longa
JWT_SECRET_KEY=sua-chave-jwt-aleatoria-muito-longa
```

### Passo 2: Estrutura de Diretórios no Coolify

Quando você fizer upload no Coolify, certifique-se de que a estrutura fica assim:
```
/data/coolify/services/y440c0o08scgo8sco4gos4sc/
├── docker-compose.yml
├── Dockerfile
├── .env
├── requirements.txt
└── app/
    ├── __init__.py
    ├── main.py
    ├── workers.py
    └── config.py
```

### Passo 3: Como Fazer Upload no Coolify

**Opção A: Via Git (Recomendado)**
1. Faça commit de todos os arquivos no seu repositório Git
2. No Coolify, conecte ao seu repositório
3. Configure o branch (main/master)
4. Deploy!

**Opção B: Upload Manual**
1. Comprima todos os arquivos em um ZIP
2. Faça upload no Coolify
3. Certifique-se de que a estrutura está correta

### Passo 4: Configurar no Coolify

1. **Tipo de Deploy**: Docker Compose
2. **Arquivo**: docker-compose.yml
3. **Variáveis de Ambiente**: 
   - Opção 1: Upload do arquivo `.env`
   - Opção 2: Configure manualmente na interface

### Passo 5: Portas a Expor

Configure no Coolify para expor:
- **80/443**: Nginx (acesso público)
- **5555**: Flower (opcional, para monitoramento)
- **9001**: MinIO Console (opcional, para gerenciar arquivos)

## 🐛 Resolvendo Erros Comuns

### ❌ Erro: "Dockerfile not found"
**Solução**: Certifique-se de que o `Dockerfile` está na raiz do projeto, no mesmo nível do `docker-compose.yml`

### ❌ Erro: "variable is not set"
**Solução**: 
1. Verifique se o arquivo `.env` foi enviado
2. OU configure as variáveis na interface do Coolify

### ❌ Erro: "backend service unhealthy"
**Solução**: 
1. Verifique os logs: `docker-compose logs backend`
2. Certifique-se de que todas as variáveis estão configuradas
3. Verifique se o PostgreSQL iniciou corretamente

## 📊 Verificar se Funcionou

Após o deploy, acesse:

1. **API Docs**: `https://seu-dominio.com/docs`
2. **Health Check**: `https://seu-dominio.com/health`
3. **Flower**: `https://seu-dominio.com:5555` (usuário: admin, senha: a que você configurou)
4. **MinIO**: `https://seu-dominio.com:9001`

## 🔒 Checklist de Segurança

Antes de colocar em produção:

- [ ] Mudei TODAS as senhas no `.env`
- [ ] Configurei `SECRET_KEY` e `JWT_SECRET_KEY` com valores aleatórios longos
- [ ] Configurei SSL/HTTPS no Coolify
- [ ] Configurei backup automático do banco de dados
- [ ] Configurei as chaves de API reais (Z-API, Helena CRM, OpenAI)
- [ ] Revisei as configurações de CORS
- [ ] Testei todos os endpoints

## 🆘 Precisa de Ajuda?

Se ainda der erro, me envie:
1. Os logs do Coolify
2. O comando exato que está falhando
3. A estrutura de diretórios que você enviou

## 📝 Próximos Passos Após Deploy

1. **Rodar migrações do banco**:
   ```bash
   docker-compose exec backend alembic upgrade head
   ```

2. **Criar usuário admin** (você precisará criar esse endpoint)

3. **Testar integrações**:
   - WhatsApp (Z-API)
   - Helena CRM
   - Upload de arquivos no MinIO

4. **Configurar monitoramento** (Sentry, logs, etc.)

---

**Dica**: Comece com um deploy simples para testar. Depois que tudo estiver funcionando, você pode adicionar mais funcionalidades!
