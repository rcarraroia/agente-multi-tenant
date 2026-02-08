# 🚀 CONFIGURAÇÃO EASYPANEL - CORS FIX

## 🚨 PROBLEMA IDENTIFICADO

O CORS não está funcionando porque as variáveis de ambiente não estão configuradas no EasyPanel.

## ✅ SOLUÇÃO

### 1. CONFIGURAR VARIÁVEIS DE AMBIENTE NO EASYPANEL

Acesse o EasyPanel Dashboard e configure estas variáveis:

```bash
# CORS - CRÍTICO!
CORS_ORIGINS=https://agente-multi-tenant.vercel.app,https://agente-multi-tenant-rcarraroias-projects.vercel.app,https://agente-multi-tenant-git-main-rcarraroias-projects.vercel.app

# Environment
ENVIRONMENT=production
DEBUG=False

# Supabase
SUPABASE_URL=https://vtynmmtuvxreiwcxxlma.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ0eW5tbXR1dnhyZWl3Y3h4bG1hIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NjM4MTYwMiwiZXhwIjoyMDcxOTU3NjAyfQ.-vh-TMWwltqy8--3Ka9Fb9ToYwRw8nkdP49QtKZ77e0
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ0eW5tbXR1dnhyZWl3Y3h4bG1hIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTYzODE2MDIsImV4cCI6MjA3MTk1NzYwMn0.fd-WSqFh7QsSlB0Q62cXAZZ-yDcI0n0sXyJ4eWIRKH8

# JWT
JWT_SECRET_KEY=_O3O3Oq58pf5dd1y8Kkfeyk0aNFQttvih26JBXzztUDIUju8QlxcYjAZdEoKZsZJC5zZvYYMc_lUxk6VCXIFyQ
JWT_ALGORITHM=HS256

# Supabase Auth JWT
SUPABASE_JWT_SECRET=HOwlz7ir1R2EvyMSy9yj+HSh25RtIVzSeORRcM9T1MlCiux5w6wGfYf9dLbyYPQnJgrfaGbb/dR1oin1cS7BnA==

# Redis
REDIS_URL=redis://localhost:6379

# OpenAI
OPENAI_API_KEY=sua-chave-openai-aqui

# Evolution API
EVOLUTION_API_URL=https://slimquality-evolution-api.wpjtfd.easypanel.host
EVOLUTION_API_KEY=Ombp1cOulPQzW3vhx9YRcF9x9b32D95mWZVwTLuF9nFxpizJlMdkvRUqH08OEy07K6eOUsVNiblaBVQ87bSDn0SoZi033ujz4on90dRm9XDJsWCFq23jEph9KmC5IIjt

# Chatwoot
CHATWOOT_URL=https://slimquality-chatwoot.wpjtfd.easypanel.host
CHATWOOT_ADMIN_TOKEN=YSEK4JiCW6HHXNvhkoj3m8pe
CHATWOOT_ACCOUNT_ID=5
CHATWOOT_INBOX_ID=1
```

### 2. REBUILD DO CONTAINER

Após configurar as variáveis:
1. Acesse o EasyPanel
2. Vá no serviço `agente-multi-tenant`
3. Clique em **"Rebuild"**
4. Aguarde o rebuild completar

### 3. VERIFICAR LOGS

Após o rebuild, verifique os logs para confirmar:
```
🌐 Configurando CORS para ambiente: production
   Origens configuradas: 3
   Origens permitidas: ['https://agente-multi-tenant.vercel.app', ...]
✅ CORS configurado com sucesso
```

### 4. TESTAR CORS

Teste no navegador:
```
https://agente-multi-tenant.vercel.app/whatsapp
```

Deve funcionar sem erros CORS.

## 🔧 ALTERNATIVA: USAR DOCKER COMPOSE

Se preferir, pode usar o docker-compose.yml com as variáveis:

```yaml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - CORS_ORIGINS=https://agente-multi-tenant.vercel.app,https://agente-multi-tenant-rcarraroias-projects.vercel.app,https://agente-multi-tenant-git-main-rcarraroias-projects.vercel.app
      - ENVIRONMENT=production
      - DEBUG=False
      # ... outras variáveis
```

## 🚨 IMPORTANTE

A variável **CORS_ORIGINS** é CRÍTICA. Sem ela, o frontend não consegue se comunicar com a API.

## ✅ RESULTADO ESPERADO

Após a configuração:
- ✅ Frontend conecta com API sem erro CORS
- ✅ Painel WhatsApp funciona
- ✅ QR Code é gerado
- ✅ Integração completa funcionando