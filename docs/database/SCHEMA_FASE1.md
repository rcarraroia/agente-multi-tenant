# Schema Banco de Dados - Fase 1

Este documento contém o schema SQL completo para a Fase 1 do Backend Core do Agente Multi-Tenant.

## Tabelas

### 1. multi_agent_tenants
Configuração central de cada afiliado.

```sql
CREATE TABLE IF NOT EXISTS public.multi_agent_tenants (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    affiliate_id uuid NOT NULL UNIQUE REFERENCES public.affiliates(id),
    status text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'canceled')),
    whatsapp_number text,
    evolution_instance_id text,
    chatwoot_inbox_id text,
    agent_name text NOT NULL DEFAULT 'BIA',
    agent_personality text,
    knowledge_enabled boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    activated_at timestamptz,
    suspended_at timestamptz
);

CREATE INDEX IF NOT EXISTS idx_multi_agent_tenants_affiliate_id ON public.multi_agent_tenants(affiliate_id);
CREATE INDEX IF NOT EXISTS idx_multi_agent_tenants_status ON public.multi_agent_tenants(status);

ALTER TABLE public.multi_agent_tenants ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Tenant isolation - SELECT" ON public.multi_agent_tenants
    FOR SELECT USING (affiliate_id IN (SELECT id FROM affiliates WHERE user_id = auth.uid()));

CREATE POLICY "Tenant isolation - UPDATE" ON public.multi_agent_tenants
    FOR UPDATE USING (affiliate_id IN (SELECT id FROM affiliates WHERE user_id = auth.uid()));
```

### 2. multi_agent_subscriptions
Controle de assinaturas recorrentes via Asaas.

```sql
CREATE TABLE IF NOT EXISTS public.multi_agent_subscriptions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL UNIQUE REFERENCES public.multi_agent_tenants(id),
    affiliate_id uuid NOT NULL REFERENCES public.affiliates(id),
    asaas_subscription_id text NOT NULL UNIQUE,
    asaas_customer_id text NOT NULL,
    status text NOT NULL CHECK (status IN ('active', 'overdue', 'canceled', 'expired')),
    plan_value_cents integer NOT NULL,
    billing_type text NOT NULL CHECK (billing_type IN ('CREDIT_CARD', 'BOLETO', 'PIX')),
    next_due_date date,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    canceled_at timestamptz
);

CREATE INDEX IF NOT EXISTS idx_multi_agent_subs_tenant_id ON public.multi_agent_subscriptions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_multi_agent_subs_asaas_id ON public.multi_agent_subscriptions(asaas_subscription_id);
CREATE INDEX IF NOT EXISTS idx_multi_agent_subs_status ON public.multi_agent_subscriptions(status);

ALTER TABLE public.multi_agent_subscriptions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Subscription isolation - SELECT" ON public.multi_agent_subscriptions
    FOR SELECT USING (tenant_id IN (SELECT id FROM multi_agent_tenants WHERE affiliate_id IN (SELECT id FROM affiliates WHERE user_id = auth.uid())));
```

### 3. multi_agent_conversations
Metadados das sessões de chat.

```sql
CREATE TABLE IF NOT EXISTS public.multi_agent_conversations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL REFERENCES public.multi_agent_tenants(id),
    customer_phone text NOT NULL,
    customer_name text,
    status text NOT NULL DEFAULT 'ai' CHECK (status IN ('ai', 'human', 'closed')),
    assigned_to_user_id uuid REFERENCES public.profiles(id),
    channel text NOT NULL DEFAULT 'whatsapp',
    last_message_at timestamptz NOT NULL DEFAULT now(),
    unread_count integer NOT NULL DEFAULT 0,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    closed_at timestamptz
);

CREATE INDEX IF NOT EXISTS idx_multi_agent_conv_tenant_id ON public.multi_agent_conversations(tenant_id);
CREATE INDEX IF NOT EXISTS idx_multi_agent_conv_status ON public.multi_agent_conversations(status);
CREATE INDEX IF NOT EXISTS idx_multi_agent_conv_last_message ON public.multi_agent_conversations(last_message_at DESC);
CREATE INDEX IF NOT EXISTS idx_multi_agent_conv_phone ON public.multi_agent_conversations(tenant_id, customer_phone);

ALTER TABLE public.multi_agent_conversations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Conversation isolation - SELECT" ON public.multi_agent_conversations
    FOR SELECT USING (tenant_id IN (SELECT id FROM multi_agent_tenants WHERE affiliate_id IN (SELECT id FROM affiliates WHERE user_id = auth.uid())));
```

### 4. multi_agent_messages
Log completo de mensagens.

```sql
CREATE TABLE IF NOT EXISTS public.multi_agent_messages (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id uuid NOT NULL REFERENCES public.multi_agent_conversations(id) ON DELETE CASCADE,
    tenant_id uuid NOT NULL REFERENCES public.multi_agent_tenants(id),
    direction text NOT NULL CHECK (direction IN ('incoming', 'outgoing')),
    sender_type text NOT NULL CHECK (sender_type IN ('customer', 'ai', 'human')),
    sender_user_id uuid REFERENCES public.profiles(id),
    content_type text NOT NULL CHECK (content_type IN ('text', 'image', 'video', 'audio', 'document')),
    content_text text,
    media_url text,
    media_mime_type text,
    whatsapp_message_id text,
    metadata jsonb DEFAULT '{}',
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_multi_agent_msg_conversation ON public.multi_agent_messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_multi_agent_msg_tenant ON public.multi_agent_messages(tenant_id);
CREATE INDEX IF NOT EXISTS idx_multi_agent_msg_created ON public.multi_agent_messages(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_multi_agent_msg_whatsapp_id ON public.multi_agent_messages(whatsapp_message_id);

ALTER TABLE public.multi_agent_messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Message isolation - SELECT" ON public.multi_agent_messages
    FOR SELECT USING (tenant_id IN (SELECT id FROM multi_agent_tenants WHERE affiliate_id IN (SELECT id FROM affiliates WHERE user_id = auth.uid())));
```

### 5. multi_agent_knowledge
Base de conhecimento (RAG).

```sql
-- Habilitar pgvector se ainda não habilitado
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS public.multi_agent_knowledge (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id uuid REFERENCES public.multi_agent_tenants(id), -- NULL = Conhecimento Global
    title text NOT NULL,
    content text NOT NULL,
    content_type text NOT NULL CHECK (content_type IN ('faq', 'product', 'policy', 'procedure')),
    is_active boolean NOT NULL DEFAULT true,
    embedding vector(1536),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_multi_agent_knowledge_tenant ON public.multi_agent_knowledge(tenant_id);
CREATE INDEX IF NOT EXISTS idx_multi_agent_knowledge_active ON public.multi_agent_knowledge(is_active);
-- Nota: Índice de vetor usando ivfflat ou hnsw pode ser adicionado após carga inicial de dados

ALTER TABLE public.multi_agent_knowledge ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Knowledge isolation - SELECT" ON public.multi_agent_knowledge
    FOR SELECT USING (
        tenant_id IS NULL OR 
        tenant_id IN (SELECT id FROM multi_agent_tenants WHERE affiliate_id IN (SELECT id FROM affiliates WHERE user_id = auth.uid()))
    );
```

### 6. multi_agent_handoffs
Registro de transferências para atendimento humano.

```sql
CREATE TABLE IF NOT EXISTS public.multi_agent_handoffs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id uuid NOT NULL REFERENCES public.multi_agent_conversations(id),
    tenant_id uuid NOT NULL REFERENCES public.multi_agent_tenants(id),
    reason text,
    chatwoot_conversation_id text,
    status text NOT NULL DEFAULT 'requested' CHECK (status IN ('requested', 'accepted', 'resolved')),
    requested_at timestamptz NOT NULL DEFAULT now(),
    accepted_at timestamptz,
    resolved_at timestamptz,
    resolved_by_user_id uuid REFERENCES public.profiles(id)
);

CREATE INDEX IF NOT EXISTS idx_multi_agent_handoff_conversation ON public.multi_agent_handoffs(conversation_id);
CREATE INDEX IF NOT EXISTS idx_multi_agent_handoff_tenant ON public.multi_agent_handoffs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_multi_agent_handoff_status ON public.multi_agent_handoffs(status);

ALTER TABLE public.multi_agent_handoffs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Handoff isolation - SELECT" ON public.multi_agent_handoffs
    FOR SELECT USING (tenant_id IN (SELECT id FROM multi_agent_tenants WHERE affiliate_id IN (SELECT id FROM affiliates WHERE user_id = auth.uid())));
```

## Triggers e Funções

```sql
-- Função para atualizar a coluna updated_at
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Aplicar a todas as tabelas relevantes
CREATE TRIGGER tr_multi_agent_tenants_updated_at BEFORE UPDATE ON public.multi_agent_tenants FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER tr_multi_agent_subscriptions_updated_at BEFORE UPDATE ON public.multi_agent_subscriptions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER tr_multi_agent_conversations_updated_at BEFORE UPDATE ON public.multi_agent_conversations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER tr_multi_agent_knowledge_updated_at BEFORE UPDATE ON public.multi_agent_knowledge FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

## Script de Execução Completo

```sql
-- HABILITAR EXTENSÕES
CREATE EXTENSION IF NOT EXISTS vector;

-- FUNÇÃO DE ATUALIZAÇÃO
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- TABELA: multi_agent_tenants
CREATE TABLE IF NOT EXISTS public.multi_agent_tenants (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    affiliate_id uuid NOT NULL UNIQUE REFERENCES public.affiliates(id),
    status text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'canceled')),
    whatsapp_number text,
    evolution_instance_id text,
    chatwoot_inbox_id text,
    agent_name text NOT NULL DEFAULT 'BIA',
    agent_personality text,
    knowledge_enabled boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    activated_at timestamptz,
    suspended_at timestamptz
);
CREATE INDEX IF NOT EXISTS idx_multi_agent_tenants_affiliate_id ON public.multi_agent_tenants(affiliate_id);
CREATE INDEX IF NOT EXISTS idx_multi_agent_tenants_status ON public.multi_agent_tenants(status);
ALTER TABLE public.multi_agent_tenants ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Tenant isolation - SELECT" ON public.multi_agent_tenants FOR SELECT USING (affiliate_id IN (SELECT id FROM affiliates WHERE user_id = auth.uid()));
CREATE POLICY "Tenant isolation - UPDATE" ON public.multi_agent_tenants FOR UPDATE USING (affiliate_id IN (SELECT id FROM affiliates WHERE user_id = auth.uid()));
CREATE TRIGGER tr_multi_agent_tenants_updated_at BEFORE UPDATE ON public.multi_agent_tenants FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- TABELA: multi_agent_subscriptions
CREATE TABLE IF NOT EXISTS public.multi_agent_subscriptions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL UNIQUE REFERENCES public.multi_agent_tenants(id),
    affiliate_id uuid NOT NULL REFERENCES public.affiliates(id),
    asaas_subscription_id text NOT NULL UNIQUE,
    asaas_customer_id text NOT NULL,
    status text NOT NULL CHECK (status IN ('active', 'overdue', 'canceled', 'expired')),
    plan_value_cents integer NOT NULL,
    billing_type text NOT NULL CHECK (billing_type IN ('CREDIT_CARD', 'BOLETO', 'PIX')),
    next_due_date date,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    canceled_at timestamptz
);
CREATE INDEX IF NOT EXISTS idx_multi_agent_subs_tenant_id ON public.multi_agent_subscriptions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_multi_agent_subs_asaas_id ON public.multi_agent_subscriptions(asaas_subscription_id);
CREATE INDEX IF NOT EXISTS idx_multi_agent_subs_status ON public.multi_agent_subscriptions(status);
ALTER TABLE public.multi_agent_subscriptions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Subscription isolation - SELECT" ON public.multi_agent_subscriptions FOR SELECT USING (tenant_id IN (SELECT id FROM multi_agent_tenants WHERE affiliate_id IN (SELECT id FROM affiliates WHERE user_id = auth.uid())));
CREATE TRIGGER tr_multi_agent_subscriptions_updated_at BEFORE UPDATE ON public.multi_agent_subscriptions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- TABELA: multi_agent_conversations
CREATE TABLE IF NOT EXISTS public.multi_agent_conversations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL REFERENCES public.multi_agent_tenants(id),
    customer_phone text NOT NULL,
    customer_name text,
    status text NOT NULL DEFAULT 'ai' CHECK (status IN ('ai', 'human', 'closed')),
    assigned_to_user_id uuid REFERENCES public.profiles(id),
    channel text NOT NULL DEFAULT 'whatsapp',
    last_message_at timestamptz NOT NULL DEFAULT now(),
    unread_count integer NOT NULL DEFAULT 0,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    closed_at timestamptz
);
CREATE INDEX IF NOT EXISTS idx_multi_agent_conv_tenant_id ON public.multi_agent_conversations(tenant_id);
CREATE INDEX IF NOT EXISTS idx_multi_agent_conv_status ON public.multi_agent_conversations(status);
CREATE INDEX IF NOT EXISTS idx_multi_agent_conv_last_message ON public.multi_agent_conversations(last_message_at DESC);
CREATE INDEX IF NOT EXISTS idx_multi_agent_conv_phone ON public.multi_agent_conversations(tenant_id, customer_phone);
ALTER TABLE public.multi_agent_conversations ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Conversation isolation - SELECT" ON public.multi_agent_conversations FOR SELECT USING (tenant_id IN (SELECT id FROM multi_agent_tenants WHERE affiliate_id IN (SELECT id FROM affiliates WHERE user_id = auth.uid())));
CREATE TRIGGER tr_multi_agent_conversations_updated_at BEFORE UPDATE ON public.multi_agent_conversations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- TABELA: multi_agent_messages
CREATE TABLE IF NOT EXISTS public.multi_agent_messages (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id uuid NOT NULL REFERENCES public.multi_agent_conversations(id) ON DELETE CASCADE,
    tenant_id uuid NOT NULL REFERENCES public.multi_agent_tenants(id),
    direction text NOT NULL CHECK (direction IN ('incoming', 'outgoing')),
    sender_type text NOT NULL CHECK (sender_type IN ('customer', 'ai', 'human')),
    sender_user_id uuid REFERENCES public.profiles(id),
    content_type text NOT NULL CHECK (content_type IN ('text', 'image', 'video', 'audio', 'document')),
    content_text text,
    media_url text,
    media_mime_type text,
    whatsapp_message_id text,
    metadata jsonb DEFAULT '{}',
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_multi_agent_msg_conversation ON public.multi_agent_messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_multi_agent_msg_tenant ON public.multi_agent_messages(tenant_id);
CREATE INDEX IF NOT EXISTS idx_multi_agent_msg_created ON public.multi_agent_messages(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_multi_agent_msg_whatsapp_id ON public.multi_agent_messages(whatsapp_message_id);
ALTER TABLE public.multi_agent_messages ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Message isolation - SELECT" ON public.multi_agent_messages FOR SELECT USING (tenant_id IN (SELECT id FROM multi_agent_tenants WHERE affiliate_id IN (SELECT id FROM affiliates WHERE user_id = auth.uid())));

-- TABELA: multi_agent_knowledge
CREATE TABLE IF NOT EXISTS public.multi_agent_knowledge (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id uuid REFERENCES public.multi_agent_tenants(id),
    title text NOT NULL,
    content text NOT NULL,
    content_type text NOT NULL CHECK (content_type IN ('faq', 'product', 'policy', 'procedure')),
    is_active boolean NOT NULL DEFAULT true,
    embedding vector(1536),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_multi_agent_knowledge_tenant ON public.multi_agent_knowledge(tenant_id);
CREATE INDEX IF NOT EXISTS idx_multi_agent_knowledge_active ON public.multi_agent_knowledge(is_active);
ALTER TABLE public.multi_agent_knowledge ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Knowledge isolation - SELECT" ON public.multi_agent_knowledge FOR SELECT USING (tenant_id IS NULL OR tenant_id IN (SELECT id FROM multi_agent_tenants WHERE affiliate_id IN (SELECT id FROM affiliates WHERE user_id = auth.uid())));
CREATE TRIGGER tr_multi_agent_knowledge_updated_at BEFORE UPDATE ON public.multi_agent_knowledge FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- TABELA: multi_agent_handoffs
CREATE TABLE IF NOT EXISTS public.multi_agent_handoffs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id uuid NOT NULL REFERENCES public.multi_agent_conversations(id),
    tenant_id uuid NOT NULL REFERENCES public.multi_agent_tenants(id),
    reason text,
    chatwoot_conversation_id text,
    status text NOT NULL DEFAULT 'requested' CHECK (status IN ('requested', 'accepted', 'resolved')),
    requested_at timestamptz NOT NULL DEFAULT now(),
    accepted_at timestamptz,
    resolved_at timestamptz,
    resolved_by_user_id uuid REFERENCES public.profiles(id)
);
CREATE INDEX IF NOT EXISTS idx_multi_agent_handoff_conversation ON public.multi_agent_handoffs(conversation_id);
CREATE INDEX IF NOT EXISTS idx_multi_agent_handoff_tenant ON public.multi_agent_handoffs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_multi_agent_handoff_status ON public.multi_agent_handoffs(status);
ALTER TABLE public.multi_agent_handoffs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Handoff isolation - SELECT" ON public.multi_agent_handoffs FOR SELECT USING (tenant_id IN (SELECT id FROM multi_agent_tenants WHERE affiliate_id IN (SELECT id FROM affiliates WHERE user_id = auth.uid())));
```
