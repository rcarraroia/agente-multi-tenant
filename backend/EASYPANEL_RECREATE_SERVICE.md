# 🚀 GUIA COMPLETO: RECRIAR SERVIÇO NO EASYPANEL

## 🎯 OBJETIVO
Recriar o serviço no EasyPanel com configuração de rede correta para resolver o problema de acesso externo.

## 📋 PASSO A PASSO DETALHADO

### PASSO 1: DELETAR SERVIÇO ATUAL
1. Acesse EasyPanel Dashboard
2. Vá em "Services"
3. Encontre `agente-multi-tenant`
4. Clique nos 3 pontinhos → "Delete"
5. Confirme a exclusão

### PASSO 2: CRIAR NOVO SERVIÇO
1. Clique em "Create Service"
2. Escolha "Docker Image"
3. Configure:

#### CONFIGURAÇÃO BÁSICA:
```
Service Name: agente-multi-tenant
Docker Image: rcarraroia/agente-multi-tenant:latest
```

#### CONFIGURAÇÃO DE PORTA:
```
Container Port: 8000
Service Port: 80
Protocol: HTTP
```

#### CONFIGURAÇÃO DE DOMÍNIO:
```
Domain: agente-multi-tenant.wpjtfd.easypanel.host
SSL: Enabled (Let's Encrypt)
```

### PASSO 3: CONFIGURAR VARIÁVEIS DE AMBIENTE

Adicione TODAS estas variáveis:

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
OPENAI_API_KEY=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

# Evolution API
EVOLUTION_API_URL=https://slimquality-evolution-api.wpjtfd.easypanel.host
EVOLUTION_API_KEY=Ombp1cOulPQzW3vhx9YRcF9x9b32D95mWZVwTLuF9nFxpizJlMdkvRUqH08OEy07K6eOUsVNiblaBVQ87bSDn0SoZi033ujz4on90dRm9XDJsWCFq23jEph9KmC5IIjt

# Chatwoot
CHATWOOT_URL=https://slimquality-chatwoot.wpjtfd.easypanel.host
CHATWOOT_ADMIN_TOKEN=YSEK4JiCW6HHXNvhkoj3m8pe
CHATWOOT_ACCOUNT_ID=5
CHATWOOT_INBOX_ID=1
```

### PASSO 4: CONFIGURAÇÕES AVANÇADAS

#### HEALTH CHECK:
```
Health Check Path: /health
Health Check Port: 8000
Health Check Interval: 30s
```

#### RECURSOS:
```
CPU: 1 core
Memory: 1GB
```

#### RESTART POLICY:
```
Restart Policy: Always
```

### PASSO 5: DEPLOY E VERIFICAÇÃO

1. Clique em "Create Service"
2. Aguarde o deploy (2-3 minutos)
3. Verifique os logs:

#### LOGS ESPERADOS:
```
🚀 Iniciando aplicação Agente Multi-Tenant
🚀 CORS FIX - CONFIGURANDO CORS ULTRA PERMISSIVO
✅ CORS ULTRA PERMISSIVO CONFIGURADO!
✅ HEADERS CORS MANUAIS ADICIONADOS!
INFO: Uvicorn running on http://0.0.0.0:8000
INFO: Application startup complete.
```

### PASSO 6: TESTAR ACESSO EXTERNO

#### TESTE 1: Health Check
```bash
curl https://agente-multi-tenant.wpjtfd.easypanel.host/health
```

**Resultado esperado:**
```json
{
  "status": "ok",
  "environment": "production",
  "version": "1.0.0"
}
```

#### TESTE 2: Root Endpoint
```bash
curl https://agente-multi-tenant.wpjtfd.easypanel.host/
```

**Resultado esperado:**
```json
{
  "message": "Welcome to Agente Multi-Tenant",
  "version": "1.0.0",
  "environment": "production",
  "api_docs": "/api/v1/docs",
  "health_check": "/api/v1/health"
}
```

#### TESTE 3: Frontend Integration
Acesse: `https://agente-multi-tenant.vercel.app/whatsapp`

**Deve funcionar sem erros CORS!**

## 🚨 TROUBLESHOOTING

### SE AINDA NÃO FUNCIONAR:

#### PROBLEMA 1: Domínio não resolve
```bash
nslookup agente-multi-tenant.wpjtfd.easypanel.host
```
**Solução:** Aguardar propagação DNS (até 24h)

#### PROBLEMA 2: SSL não funciona
```bash
curl -k https://agente-multi-tenant.wpjtfd.easypanel.host/health
```
**Solução:** Verificar certificado Let's Encrypt no EasyPanel

#### PROBLEMA 3: Container não inicia
**Verificar logs no EasyPanel:**
- Erro de variáveis de ambiente?
- Erro de dependências?
- Erro de porta?

#### PROBLEMA 4: 502 Bad Gateway
**Possíveis causas:**
- Container não está rodando na porta 8000
- Health check falhando
- Traefik não consegue conectar

## ✅ CHECKLIST FINAL

- [ ] Serviço antigo deletado
- [ ] Novo serviço criado com nome correto
- [ ] Imagem Docker correta configurada
- [ ] Porta 8000 → 80 mapeada
- [ ] Domínio configurado com SSL
- [ ] Todas as variáveis de ambiente adicionadas
- [ ] Health check configurado
- [ ] Deploy concluído sem erros
- [ ] Logs mostram aplicação rodando
- [ ] Teste curl funciona
- [ ] Frontend conecta sem erro CORS

## 🎯 RESULTADO ESPERADO

Após seguir este guia:
- ✅ API acessível externamente
- ✅ CORS funcionando
- ✅ Frontend conecta com backend
- ✅ Sistema completo funcionando

**TEMPO ESTIMADO:** 10-15 minutos