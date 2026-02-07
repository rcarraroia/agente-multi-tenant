# Deploy FastAPI no EasyPanel

## 📋 Pré-requisitos

- [x] Dockerfile otimizado criado
- [x] Health check endpoint `/health` implementado
- [x] Variáveis de ambiente configuradas
- [x] Credenciais dos serviços EasyPanel descobertas

## 🚀 Configuração no EasyPanel

### 1. Criar Nova Aplicação

1. **Acessar EasyPanel Dashboard**
2. **Criar novo App:**
   - Nome: `agente-multi-tenant`
   - Tipo: `Docker`
   - Source: `GitHub Repository`

### 2. Configuração Docker

```yaml
# Configuração da aplicação
Name: agente-multi-tenant
Port: 8000
Build Context: ./backend
Dockerfile: ./Dockerfile
```

### 3. Variáveis de Ambiente

**CRÍTICAS - Configurar no EasyPanel:**

```bash
# Supabase (UNIFICADO)
SUPABASE_URL=https://vtynmmtuvxreiwcxxlma.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ0eW5tbXR1dnhyZWl3Y3h4bG1hIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NjM4MTYwMiwiZXhwIjoyMDcxOTU3NjAyfQ.-vh-TMWwltqy8--3Ka9Fb9ToYwRw8nkdP49QtKZ77e0
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ0eW5tbXR1dnhyZWl3Y3h4bG1hIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTYzODE2MDIsImV4cCI6MjA3MTk1NzYwMn0.fd-WSqFh7QsSlB0Q62cXAZZ-yDcI0n0sXyJ4eWIRKH8
SUPABASE_JWT_SECRET=HOwlz7ir1R2EvyMSy9yj+HSh25RtIVzSeORRcM9T1MlCiux5w6wGfYf9dLbyYPQnJgrfaGbb/dR1oin1cS7BnA==

# JWT
JWT_SECRET=your-secure-jwt-secret-change-in-production
JWT_ALGORITHM=HS256

# Redis (Networking interno EasyPanel)
REDIS_URL=redis://redis:6379

# OpenAI
OPENAI_API_KEY=sk-proj-your-openai-api-key-here
OPENAI_MODEL=gpt-4o-mini
AGENT_TEMPERATURE=0.7

# Evolution API (URLs internas EasyPanel)
EVOLUTION_API_URL=https://slimquality-evolution-api.wpjtfd.easypanel.host
EVOLUTION_API_KEY=Ombp1cOulPQzW3vhx9YRcF9x9b32D95mWZVwTLuF9nFxpizJlMdkvRUqH08OEy07K6eOUsVNiblaBVQ87bSDn0SoZi033ujz4on90dRm9XDJsWCFq23jEph9KmC5IIjt

# Chatwoot (URLs internas EasyPanel)
CHATWOOT_URL=https://slimquality-chatwoot.wpjtfd.easypanel.host
CHATWOOT_ADMIN_TOKEN=YSEK4JiCW6HHXNvhkoj3m8pe
CHATWOOT_ACCOUNT_ID=5
CHATWOOT_INBOX_ID=1

# CORS
CORS_ORIGINS=https://agente.slimquality.com,http://localhost:5173

# App Config
ENVIRONMENT=production
LOG_LEVEL=info
DEBUG=false
TZ=America/Sao_Paulo
```

### 4. Configuração de Rede

**Networking Interno EasyPanel:**
- FastAPI deve conseguir acessar Redis interno
- FastAPI deve conseguir acessar Evolution API
- FastAPI deve conseguir acessar Chatwoot
- Todas as comunicações internas via rede Docker do EasyPanel

### 5. Health Check

**Endpoint configurado:** `GET /health`

**Resposta esperada:**
```json
{
  "status": "ok",
  "environment": "production",
  "version": "1.0.0"
}
```

**Configuração EasyPanel:**
- Health Check Path: `/health`
- Health Check Port: `8000`
- Health Check Interval: `30s`
- Health Check Timeout: `10s`
- Health Check Retries: `3`

## 🔧 Comandos de Deploy

### Build Local (Teste)
```bash
cd agente-multi-tenant/backend
docker build -t agente-multi-tenant:latest .
docker run -p 8000:8000 --env-file .env agente-multi-tenant:latest
```

### Testar Health Check
```bash
curl http://localhost:8000/health
# Resposta esperada: {"status":"ok","environment":"production","version":"1.0.0"}
```

### Testar API
```bash
curl http://localhost:8000/api/v1/
# Deve retornar endpoints disponíveis
```

## 🌐 URLs de Produção

Após deploy no EasyPanel:

- **API Base:** `https://agente-multi-tenant.wpjtfd.easypanel.host`
- **Health Check:** `https://agente-multi-tenant.wpjtfd.easypanel.host/health`
- **API v1:** `https://agente-multi-tenant.wpjtfd.easypanel.host/api/v1/`
- **Docs:** `https://agente-multi-tenant.wpjtfd.easypanel.host/api/v1/docs`

## ✅ Validação Pós-Deploy

### 1. Health Check
```bash
curl https://agente-multi-tenant.wpjtfd.easypanel.host/health
```

### 2. Conectividade Supabase
```bash
curl -X GET "https://agente-multi-tenant.wpjtfd.easypanel.host/api/v1/tenants" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 3. Conectividade Redis
- Verificar logs da aplicação
- Não deve haver erros de conexão Redis

### 4. Conectividade Evolution API
```bash
curl -X GET "https://agente-multi-tenant.wpjtfd.easypanel.host/api/v1/whatsapp/status" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 5. Conectividade Chatwoot
```bash
curl -X GET "https://agente-multi-tenant.wpjtfd.easypanel.host/api/v1/crm/status" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## 🚨 Troubleshooting

### Problema: Container não inicia
- Verificar logs no EasyPanel
- Verificar variáveis de ambiente
- Verificar se Dockerfile build passou

### Problema: Health check falha
- Verificar se porta 8000 está exposta
- Verificar se endpoint `/health` responde
- Verificar logs da aplicação

### Problema: Erro de conexão Supabase
- Verificar SUPABASE_URL
- Verificar SUPABASE_SERVICE_KEY
- Verificar conectividade de rede

### Problema: Erro de conexão Redis
- Verificar REDIS_URL
- Verificar se Redis está rodando na rede interna
- Testar com `redis://redis:6379` ou `redis://chatwoot-redis:6379`

### Problema: Erro de conexão Evolution/Chatwoot
- Verificar URLs internas
- Verificar API keys
- Verificar se serviços estão rodando

## 📝 Logs

**Visualizar logs no EasyPanel:**
1. Acessar Dashboard
2. Ir em Apps > agente-multi-tenant
3. Clicar em "Logs"
4. Monitorar erros de startup e runtime

**Logs importantes:**
- Startup da aplicação
- Conexões com Supabase
- Conexões com Redis
- Conexões com Evolution API
- Conexões com Chatwoot
- Health check requests

---

**Status:** ✅ Pronto para deploy  
**Última atualização:** 06/02/2026  
**Responsável:** Kiro AI