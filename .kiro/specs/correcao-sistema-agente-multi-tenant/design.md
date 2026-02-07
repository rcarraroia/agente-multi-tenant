# CORREÇÃO SISTEMA AGENTE MULTI-TENANT - DESIGN

## ⚠️ ATENÇÃO - RESPOSTAS SEMPRE EM PORTUGUES-BR

## 🏗️ ARQUITETURA DO SISTEMA

### **VISÃO GERAL**
Sistema multi-tenant de agentes IA deployado no EasyPanel, com backend FastAPI, frontend React, banco Supabase e integrações WhatsApp via Evolution API.

### **COMPONENTES PRINCIPAIS**

```
┌─────────────────────────────────────────────────────────────┐
│                    EASYPANEL DEPLOYMENT                     │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌─────────────────┐                │
│  │   FRONTEND      │    │    BACKEND      │                │
│  │   React/Vite    │◄──►│   FastAPI       │                │
│  │   Port: 3000    │    │   Port: 8000    │                │
│  └─────────────────┘    └─────────────────┘                │
│           │                       │                         │
│           ▼                       ▼                         │
│  ┌─────────────────────────────────────────────────────────┐│
│  │              EXTERNAL SERVICES                          ││
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐      ││
│  │  │  SUPABASE   │ │ EVOLUTION   │ │   OPENAI    │      ││
│  │  │  Database   │ │ WhatsApp    │ │     API     │      ││
│  │  └─────────────┘ └─────────────┘ └─────────────┘      ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

## 🔧 DESIGN TÉCNICO

### **BACKEND (FastAPI)**

#### **Estrutura de Pastas**
```
backend/
├── src/
│   ├── api/                 # Endpoints REST
│   │   ├── v1/
│   │   │   ├── auth/        # Autenticação
│   │   │   ├── agents/      # Gestão de agentes
│   │   │   ├── funnels/     # Sistema de funis
│   │   │   ├── whatsapp/    # Integração WhatsApp
│   │   │   └── tenants/     # Multi-tenant
│   │   └── health/          # Health checks
│   ├── core/                # Configurações centrais
│   │   ├── config.py        # Configurações
│   │   ├── database.py      # Conexão DB
│   │   ├── security.py      # Segurança/JWT
│   │   └── logging.py       # Sistema de logs
│   ├── models/              # Modelos Pydantic
│   ├── services/            # Lógica de negócio
│   │   ├── agent_service.py
│   │   ├── funnel_service.py
│   │   ├── whatsapp_service.py
│   │   └── tenant_service.py
│   ├── integrations/        # Integrações externas
│   │   ├── supabase.py
│   │   ├── evolution_api.py
│   │   └── openai_client.py
│   └── utils/               # Utilitários
├── tests/                   # Testes
├── requirements.txt         # Dependências
├── Dockerfile              # Container
└── main.py                 # Entry point
```

#### **Configurações Críticas**
```python
# core/config.py
class Settings:
    # Database
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_SERVICE_KEY: str
    
    # WhatsApp Integration
    EVOLUTION_API_URL: str
    EVOLUTION_API_KEY: str
    
    # OpenAI
    OPENAI_API_KEY: str
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
```

#### **Sistema de Logs**
```python
# core/logging.py
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "module": record.name,
            "message": record.getMessage(),
            "tenant_id": getattr(record, 'tenant_id', None),
            "user_id": getattr(record, 'user_id', None)
        }
        return json.dumps(log_entry)

def setup_logging():
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
```

### **FRONTEND (React/Vite)**

#### **Estrutura de Pastas**
```
frontend/
├── src/
│   ├── components/          # Componentes reutilizáveis
│   │   ├── ui/             # Componentes base
│   │   ├── forms/          # Formulários
│   │   └── layout/         # Layout components
│   ├── pages/              # Páginas da aplicação
│   │   ├── Dashboard/
│   │   ├── Agents/
│   │   ├── Funnels/
│   │   ├── WhatsApp/
│   │   └── Settings/
│   ├── services/           # Serviços API
│   │   ├── api.ts          # Cliente HTTP
│   │   ├── auth.service.ts
│   │   ├── agent.service.ts
│   │   ├── funnel.service.ts
│   │   └── whatsapp.service.ts
│   ├── hooks/              # Custom hooks
│   ├── store/              # Estado global (Zustand)
│   ├── types/              # TypeScript types
│   └── utils/              # Utilitários
├── public/
├── package.json
├── vite.config.ts
└── Dockerfile
```

#### **Gerenciamento de Estado**
```typescript
// store/useAppStore.ts
interface AppState {
  // Auth
  user: User | null;
  token: string | null;
  tenant: Tenant | null;
  
  // UI State
  loading: boolean;
  error: string | null;
  
  // Data
  agents: Agent[];
  funnels: Funnel[];
  whatsappInstances: WhatsAppInstance[];
  
  // Actions
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => void;
  setError: (error: string | null) => void;
  fetchAgents: () => Promise<void>;
  fetchFunnels: () => Promise<void>;
}
```

## 🗄️ DESIGN DO BANCO DE DADOS

### **Tabelas Principais**

#### **Tenants (Multi-tenancy)**
```sql
CREATE TABLE tenants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  slug VARCHAR(100) UNIQUE NOT NULL,
  plan VARCHAR(50) NOT NULL DEFAULT 'basic',
  status VARCHAR(20) NOT NULL DEFAULT 'active',
  settings JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### **Users (Usuários por tenant)**
```sql
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  role VARCHAR(50) NOT NULL DEFAULT 'user',
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### **Agents (Agentes IA)**
```sql
CREATE TABLE agents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  prompt TEXT NOT NULL,
  model VARCHAR(100) DEFAULT 'gpt-4',
  temperature DECIMAL(3,2) DEFAULT 0.7,
  max_tokens INTEGER DEFAULT 1000,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### **Funnels (Funis de conversação)**
```sql
CREATE TABLE funnels (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
  agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  steps JSONB NOT NULL DEFAULT '[]',
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### **WhatsApp Instances**
```sql
CREATE TABLE whatsapp_instances (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
  instance_name VARCHAR(255) NOT NULL,
  instance_key VARCHAR(255) NOT NULL,
  status VARCHAR(50) DEFAULT 'disconnected',
  qr_code TEXT,
  webhook_url TEXT,
  settings JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### **Row Level Security (RLS)**
```sql
-- Habilitar RLS em todas as tabelas
ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE agents ENABLE ROW LEVEL SECURITY;
ALTER TABLE funnels ENABLE ROW LEVEL SECURITY;
ALTER TABLE whatsapp_instances ENABLE ROW LEVEL SECURITY;

-- Políticas de acesso por tenant
CREATE POLICY "Users can only access their tenant data" ON agents
  FOR ALL USING (tenant_id = current_setting('app.current_tenant_id')::UUID);

CREATE POLICY "Users can only access their tenant data" ON funnels
  FOR ALL USING (tenant_id = current_setting('app.current_tenant_id')::UUID);

CREATE POLICY "Users can only access their tenant data" ON whatsapp_instances
  FOR ALL USING (tenant_id = current_setting('app.current_tenant_id')::UUID);
```

## 🔌 DESIGN DAS INTEGRAÇÕES

### **Evolution API (WhatsApp)**

#### **Configuração de Instância**
```python
# services/whatsapp_service.py
class WhatsAppService:
    def __init__(self):
        self.evolution_url = settings.EVOLUTION_API_URL
        self.api_key = settings.EVOLUTION_API_KEY
    
    async def create_instance(self, tenant_id: str, instance_name: str):
        """Criar nova instância WhatsApp"""
        payload = {
            "instanceName": instance_name,
            "token": self.api_key,
            "qrcode": True,
            "webhook": f"{settings.BASE_URL}/api/v1/whatsapp/webhook/{tenant_id}"
        }
        
        response = await self.http_client.post(
            f"{self.evolution_url}/instance/create",
            json=payload
        )
        
        return response.json()
    
    async def get_qr_code(self, instance_name: str):
        """Obter QR Code para conexão"""
        response = await self.http_client.get(
            f"{self.evolution_url}/instance/qrcode/{instance_name}"
        )
        return response.json()
```

#### **Webhook Handler**
```python
# api/v1/whatsapp.py
@router.post("/webhook/{tenant_id}")
async def whatsapp_webhook(
    tenant_id: str,
    webhook_data: dict,
    db: Session = Depends(get_db)
):
    """Processar mensagens recebidas do WhatsApp"""
    
    # Definir contexto do tenant
    await db.execute(
        text("SET app.current_tenant_id = :tenant_id"),
        {"tenant_id": tenant_id}
    )
    
    # Processar mensagem
    message = webhook_data.get("data", {})
    
    if message.get("messageType") == "conversation":
        # Buscar agente associado
        agent = await get_agent_for_instance(
            db, webhook_data.get("instance")
        )
        
        if agent:
            # Processar com IA
            response = await process_message_with_ai(
                agent, message.get("message", {}).get("conversation")
            )
            
            # Enviar resposta
            await send_whatsapp_message(
                webhook_data.get("instance"),
                message.get("key", {}).get("remoteJid"),
                response
            )
    
    return {"status": "processed"}
```

### **Supabase Integration**

#### **Database Client**
```python
# integrations/supabase.py
from supabase import create_client, Client

class SupabaseClient:
    def __init__(self):
        self.client: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY
        )
    
    async def set_tenant_context(self, tenant_id: str):
        """Definir contexto do tenant para RLS"""
        await self.client.rpc(
            'set_config',
            {
                'setting_name': 'app.current_tenant_id',
                'setting_value': tenant_id,
                'is_local': True
            }
        )
    
    async def get_agents(self, tenant_id: str):
        """Buscar agentes do tenant"""
        await self.set_tenant_context(tenant_id)
        
        response = self.client.table('agents').select('*').execute()
        return response.data
```

## 🚀 DESIGN DO DEPLOYMENT

### **EasyPanel Configuration**

#### **Docker Compose Structure**
```yaml
# docker-compose.yml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_KEY=${SUPABASE_KEY}
      - EVOLUTION_API_URL=${EVOLUTION_API_URL}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - VITE_API_URL=http://backend:8000
    depends_on:
      - backend
    restart: unless-stopped
```

#### **Health Checks**
```python
# api/health.py
@router.get("/health")
async def health_check():
    """Health check endpoint"""
    checks = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {}
    }
    
    # Check database
    try:
        await supabase_client.client.table('tenants').select('count').execute()
        checks["services"]["database"] = "healthy"
    except Exception as e:
        checks["services"]["database"] = f"unhealthy: {str(e)}"
        checks["status"] = "unhealthy"
    
    # Check Evolution API
    try:
        response = await http_client.get(f"{settings.EVOLUTION_API_URL}/instance/fetchInstances")
        if response.status_code == 200:
            checks["services"]["evolution_api"] = "healthy"
        else:
            checks["services"]["evolution_api"] = f"unhealthy: status {response.status_code}"
            checks["status"] = "unhealthy"
    except Exception as e:
        checks["services"]["evolution_api"] = f"unhealthy: {str(e)}"
        checks["status"] = "unhealthy"
    
    return checks
```

## 📊 DESIGN DE MONITORAMENTO

### **Logging Strategy**
```python
# utils/logger.py
import structlog

logger = structlog.get_logger()

# Usage examples:
logger.info("Agent created", agent_id=agent.id, tenant_id=tenant.id)
logger.error("WhatsApp connection failed", instance=instance_name, error=str(e))
logger.warning("Rate limit approaching", tenant_id=tenant.id, usage=current_usage)
```

### **Metrics Collection**
```python
# utils/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Metrics
message_counter = Counter('whatsapp_messages_total', 'Total WhatsApp messages', ['tenant_id', 'direction'])
response_time = Histogram('api_response_time_seconds', 'API response time', ['endpoint'])
active_instances = Gauge('whatsapp_instances_active', 'Active WhatsApp instances', ['tenant_id'])

# Usage
message_counter.labels(tenant_id=tenant.id, direction='incoming').inc()
response_time.labels(endpoint='/api/v1/agents').observe(0.5)
```

---

**ESTE DOCUMENTO DEFINE O DESIGN TÉCNICO COMPLETO PARA A CORREÇÃO DO SISTEMA**

**Status:** Aprovado  
**Data:** 06/02/2026  
**Responsável:** Kiro AI  
**Aprovado por:** Renato Carraro