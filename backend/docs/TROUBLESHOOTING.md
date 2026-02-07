# 🔧 GUIA DE TROUBLESHOOTING - AGENTE MULTI-TENANT

## ⚠️ ATENÇÃO - RESPOSTAS SEMPRE EM PORTUGUES-BR

Este documento fornece procedimentos de diagnóstico e resolução de problemas comuns no sistema Agente Multi-Tenant.

---

## 📋 ÍNDICE

1. [Verificações Básicas](#verificações-básicas)
2. [Problemas de Consistência de Dados](#problemas-de-consistência-de-dados)
3. [Problemas de Serviços Externos](#problemas-de-serviços-externos)
4. [Problemas de Autenticação](#problemas-de-autenticação)
5. [Problemas de Performance](#problemas-de-performance)
6. [Comandos de Diagnóstico](#comandos-de-diagnóstico)
7. [Logs e Monitoramento](#logs-e-monitoramento)

---

## 🔍 VERIFICAÇÕES BÁSICAS

### 1. Status Geral do Sistema

```bash
# Verificar health check básico
curl http://localhost:8000/health

# Verificar health check detalhado
curl http://localhost:8000/health/detailed

# Verificar dashboard de monitoramento
curl http://localhost:8000/api/v1/monitoring/dashboard
```

### 2. Conectividade com Supabase

```bash
# Testar conexão com Supabase
python -c "
from app.db.supabase import get_supabase
supabase = get_supabase()
result = supabase.table('affiliates').select('count').execute()
print('Conexão Supabase OK:', len(result.data) >= 0)
"
```

### 3. Variáveis de Ambiente

```bash
# Verificar configuração
python -c "
from app.core.config_manager import ConfigurationManager
config = ConfigurationManager()
validation = config.validate_production_config()
print('Configuração válida:', validation['is_valid'])
if not validation['is_valid']:
    for error in validation['errors']:
        print('ERRO:', error)
"
```

---

## 📊 PROBLEMAS DE CONSISTÊNCIA DE DADOS

### Sintomas
- Dados inconsistentes entre `affiliate_services` e `multi_agent_subscriptions`
- Afiliados com assinatura mas sem serviço (ou vice-versa)
- Conflitos de status ou datas entre tabelas

### Diagnóstico

```bash
# Verificar consistência geral
python -m app.commands.sync_subscriptions validate

# Verificar assinatura específica
python -m app.commands.sync_subscriptions show <AFFILIATE_ID>

# Executar verificação via API
curl -X POST http://localhost:8000/api/v1/monitoring/consistency/check
```

### Resolução

```bash
# 1. Fazer backup dos dados (SEMPRE!)
python -c "
from app.db.supabase import get_supabase
import json
from datetime import datetime

supabase = get_supabase()

# Backup affiliate_services
services = supabase.table('affiliate_services').select('*').execute()
with open(f'backup_services_{datetime.now().strftime(\"%Y%m%d_%H%M%S\")}.json', 'w') as f:
    json.dump(services.data, f, indent=2, default=str)

# Backup multi_agent_subscriptions  
subscriptions = supabase.table('multi_agent_subscriptions').select('*').execute()
with open(f'backup_subscriptions_{datetime.now().strftime(\"%Y%m%d_%H%M%S\")}.json', 'w') as f:
    json.dump(subscriptions.data, f, indent=2, default=str)

print('Backup criado com sucesso!')
"

# 2. Executar sincronização em modo dry-run (testar)
python -m app.commands.sync_subscriptions sync --dry-run --resolve-conflicts

# 3. Se tudo OK, executar sincronização real
python -m app.commands.sync_subscriptions sync --resolve-conflicts

# 4. Validar resultado
python -m app.commands.sync_subscriptions validate
```

### Prevenção

```bash
# Configurar monitoramento automático
python -c "
import asyncio
from app.services.consistency_monitor import ConsistencyMonitor

async def setup_monitoring():
    monitor = ConsistencyMonitor()
    # Configurar thresholds mais baixos para alertas precoces
    monitor.alert_thresholds = {
        'missing_services': 1,
        'missing_subscriptions': 1, 
        'status_mismatches': 3,
        'date_conflicts': 5
    }
    print('Monitoramento configurado para alertas precoces')

asyncio.run(setup_monitoring())
"
```

---

## 🌐 PROBLEMAS DE SERVIÇOS EXTERNOS

### Sintomas
- Evolution API retornando 404 ou timeout
- Chatwoot não respondendo
- OpenAI API com erros de autenticação

### Diagnóstico

```bash
# Verificar status de todos os serviços
python test_external_services.py

# Verificar circuit breakers
curl http://localhost:8000/health/circuit-breakers

# Verificar métricas de serviços
curl http://localhost:8000/api/v1/monitoring/metrics/services
```

### Resolução por Serviço

#### Evolution API
```bash
# Verificar se Evolution API está rodando no EasyPanel
# URL interna: http://evolution-api:8080

# Testar conectividade interna
python -c "
import requests
try:
    response = requests.get('http://evolution-api:8080/manager/instance', timeout=10)
    print('Evolution API Status:', response.status_code)
except Exception as e:
    print('Evolution API Error:', str(e))
"

# Verificar configuração
echo "EVOLUTION_API_URL: $EVOLUTION_API_URL"
echo "EVOLUTION_API_KEY: $EVOLUTION_API_KEY"
```

#### Chatwoot
```bash
# Verificar se Chatwoot está rodando
# URL interna: http://chatwoot:3000

# Testar API
python -c "
import requests
import os
try:
    headers = {'api_access_token': os.getenv('CHATWOOT_API_KEY')}
    response = requests.get('http://chatwoot:3000/api/v1/accounts', headers=headers, timeout=10)
    print('Chatwoot Status:', response.status_code)
except Exception as e:
    print('Chatwoot Error:', str(e))
"

# Verificar configuração
echo "CHATWOOT_URL: $CHATWOOT_URL"
echo "CHATWOOT_API_KEY: $CHATWOOT_API_KEY"
```

#### OpenAI API
```bash
# Testar OpenAI API
python -c "
import openai
import os
try:
    client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    models = client.models.list()
    print('OpenAI API OK - Modelos disponíveis:', len(models.data))
except Exception as e:
    print('OpenAI API Error:', str(e))
"

# Verificar configuração
echo "OPENAI_API_KEY: ${OPENAI_API_KEY:0:10}..."
```

### Reset de Circuit Breakers

```bash
# Reset manual de circuit breakers
python -c "
from app.services.external_service_validator import external_service_validator
external_service_validator.reset_all_circuit_breakers()
print('Circuit breakers resetados')
"
```

---

## 🔐 PROBLEMAS DE AUTENTICAÇÃO

### Sintomas
- JWT tokens inválidos
- Erro 401 em endpoints protegidos
- Problemas de resolução de tenant

### Diagnóstico

```bash
# Verificar configuração JWT
python -c "
from app.core.security import JWTSecurityManager
security = JWTSecurityManager()
validation = security.validate_jwt_configuration()
print('JWT Config válida:', validation['is_secure'])
if not validation['is_secure']:
    for issue in validation['security_issues']:
        print('PROBLEMA:', issue)
"

# Testar token específico
python -c "
from app.api.deps import get_current_user_from_token
token = 'SEU_TOKEN_AQUI'
try:
    user = get_current_user_from_token(token)
    print('Token válido para usuário:', user.get('sub'))
except Exception as e:
    print('Token inválido:', str(e))
"
```

### Resolução

```bash
# 1. Verificar secret JWT
echo "JWT_SECRET_KEY deve ter pelo menos 32 caracteres"
echo "Atual: ${JWT_SECRET_KEY:0:10}... (${#JWT_SECRET_KEY} chars)"

# 2. Verificar algoritmo
echo "JWT_ALGORITHM: $JWT_ALGORITHM (deve ser HS256 ou RS256)"

# 3. Testar endpoint de refresh
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Authorization: Bearer SEU_TOKEN_AQUI"

# 4. Verificar logs de autenticação
tail -f logs/app.log | grep "authentication"
```

---

## ⚡ PROBLEMAS DE PERFORMANCE

### Sintomas
- Tempo de resposta alto (>2s)
- Timeout em operações
- Alta utilização de CPU/memória

### Diagnóstico

```bash
# Verificar métricas de sistema
curl http://localhost:8000/api/v1/monitoring/metrics/system

# Verificar performance de endpoints
curl http://localhost:8000/api/v1/monitoring/metrics

# Verificar logs de performance
tail -f logs/app.log | grep "performance"
```

### Resolução

```bash
# 1. Verificar queries lentas
python -c "
from app.api.v1.monitoring import _metrics_store
slow_queries = [q for q in _metrics_store['database_queries'] if q.get('duration_ms', 0) > 1000]
print(f'Queries lentas (>1s): {len(slow_queries)}')
for query in slow_queries[-5:]:
    print(f'  - {query[\"query_type\"]} em {query[\"table\"]}: {query[\"duration_ms\"]}ms')
"

# 2. Verificar conexões de banco
python -c "
from app.db.supabase import get_supabase
import time
start = time.time()
supabase = get_supabase()
result = supabase.table('affiliates').select('count').limit(1).execute()
duration = (time.time() - start) * 1000
print(f'Tempo de conexão Supabase: {duration:.2f}ms')
"

# 3. Otimizar configurações
echo 'Verificar configurações de timeout e pool de conexões'
```

---

## 🛠️ COMANDOS DE DIAGNÓSTICO

### Verificação Completa do Sistema

```bash
#!/bin/bash
# Script de diagnóstico completo

echo "🔍 DIAGNÓSTICO COMPLETO DO SISTEMA"
echo "=================================="

echo -e "\n1. Health Check Básico:"
curl -s http://localhost:8000/health | jq '.'

echo -e "\n2. Serviços Externos:"
python test_external_services.py

echo -e "\n3. Consistência de Dados:"
python -m app.commands.sync_subscriptions validate

echo -e "\n4. Métricas de Sistema:"
curl -s http://localhost:8000/api/v1/monitoring/metrics/system | jq '.cpu, .memory'

echo -e "\n5. Circuit Breakers:"
curl -s http://localhost:8000/health/circuit-breakers | jq '.'

echo -e "\n6. Configuração:"
python -c "
from app.core.config_manager import ConfigurationManager
config = ConfigurationManager()
validation = config.validate_production_config()
print('Configuração válida:', validation['is_valid'])
"

echo -e "\n✅ Diagnóstico concluído!"
```

### Comandos de Manutenção

```bash
# Limpeza de logs antigos
find logs/ -name "*.log" -mtime +7 -delete

# Limpeza de métricas em memória
python -c "
from app.api.v1.monitoring import _metrics_store
for key in _metrics_store:
    _metrics_store[key] = _metrics_store[key][-100:]  # Manter apenas últimos 100
print('Cache de métricas limpo')
"

# Restart de serviços (se necessário)
# systemctl restart agente-multi-tenant
```

---

## 📊 LOGS E MONITORAMENTO

### Localização dos Logs

```bash
# Logs principais
tail -f logs/app.log

# Logs de erro
tail -f logs/error.log

# Logs de auditoria
tail -f logs/audit.log

# Logs estruturados (JSON)
tail -f logs/structured.log | jq '.'
```

### Filtros Úteis

```bash
# Erros críticos
grep "CRITICAL\|ERROR" logs/app.log

# Problemas de autenticação
grep "authentication\|jwt\|token" logs/app.log

# Problemas de consistência
grep "consistency\|sync\|conflict" logs/app.log

# Performance issues
grep "slow\|timeout\|performance" logs/app.log

# Serviços externos
grep "evolution\|chatwoot\|openai" logs/app.log
```

### Monitoramento em Tempo Real

```bash
# Dashboard completo
watch -n 30 'curl -s http://localhost:8000/api/v1/monitoring/dashboard | jq ".summary"'

# Status de consistência
watch -n 60 'curl -s http://localhost:8000/api/v1/monitoring/metrics/consistency | jq ".data_consistency.overall_status"'

# Métricas de serviços
watch -n 30 'curl -s http://localhost:8000/api/v1/monitoring/metrics/services | jq ".external_services"'
```

---

## 🚨 ALERTAS E ESCALAÇÃO

### Níveis de Severidade

1. **CRITICAL** - Sistema indisponível, dados corrompidos
   - Ação: Intervenção imediata necessária
   - Escalação: Administrador do sistema

2. **HIGH** - Funcionalidade principal comprometida
   - Ação: Resolver em até 1 hora
   - Escalação: Equipe de desenvolvimento

3. **MEDIUM** - Degradação de performance ou funcionalidade secundária
   - Ação: Resolver em até 4 horas
   - Escalação: Equipe de suporte

4. **LOW** - Problemas menores, não afetam usuários
   - Ação: Resolver em até 24 horas
   - Escalação: Manutenção programada

### Procedimento de Escalação

1. **Identificar o problema** usando este guia
2. **Coletar logs e evidências** relevantes
3. **Tentar resolução básica** conforme procedimentos
4. **Se não resolver**, escalar conforme severidade
5. **Documentar a resolução** para referência futura

---

## 📞 CONTATOS DE SUPORTE

- **Administrador do Sistema**: [definir]
- **Equipe de Desenvolvimento**: [definir]
- **Suporte Técnico**: [definir]

---

**Documento criado em:** 06/02/2026  
**Última atualização:** 06/02/2026  
**Versão:** 1.0.0