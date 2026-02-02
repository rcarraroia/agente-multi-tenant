# Auditoria de Banco de Dados - Projeto Slim Quality

**Data:** 21/01/2026
**Projeto ID:** `vtynmmtuvxreiwcxxlma` (Slim Quality)

## 1. Tabelas `agent_*` Existentes

O banco de dados já possui tabelas com o prefixo `agent_`, indicando implementações anteriores ou parciais do sistema de agentes.

### 1.1 `agent_config`
Armazena configurações globais de modelos de IA.
- **Colunas:**
  - `id` (uuid, PK)
  - `model` (varchar)
  - `temperature` (numeric)
  - `max_tokens` (integer)
  - `system_prompt` (text)
  - `sicc_enabled` (boolean)
  - `created_at`, `updated_at` (timestamptz)
- **RLS:** Ativo. Políticas para Admins (SELECT) e Super Admins (UPDATE).

### 1.2 `agent_performance_metrics`
Registra métricas de desempenho dos sub-agentes.
- **Colunas:**
  - `id` (uuid, PK)
  - `metric_type` (varchar)
  - `metric_value` (double precision)
  - `sub_agent_id` (uuid, FK para `sub_agents`)
  - `pattern_id` (uuid)
  - `measurement_date` (date)
  - `metadata` (jsonb)
  - `created_at` (timestamptz)
- **RLS:** Ativo. Política `Allow all access to performance_metrics` (ALL para public) - **Risco de Segurança identificado**.

---

## 2. Tabelas Core Slim Quality

Estrutura das tabelas base que serão reutilizadas pelo Agente Multi-Tenant.

### 2.1 `affiliates`
- **Colunas principais:** `id`, `user_id`, `name`, `email`, `referral_code`, `wallet_id`, `status`.
- **Uso:** Será o `tenant_id` principal ou relacionado ao `agent_tenants`.

### 2.2 `profiles`
- **Colunas principais:** `id`, `full_name`, `email`, `role`, `is_affiliate`, `affiliate_status`.
- **Uso:** Autenticação e controle de acesso.

### 2.3 `commissions`
- **Colunas principais:** `id`, `affiliate_id`, `amount_cents`, `status`, `description`.
- **Uso:** Registro de comissões geradas pela assinatura do agente.

### 2.4 Assinaturas (Status)
- **Nota:** Não foi encontrada uma tabela chamada `subscriptions` ou `asaas_subscriptions` no schema public. Os dados parecem estar distribuídos em `asaas_transactions` ou vinculados diretamente ao status no `profiles`/`affiliates`.
- **Tabelas relacionadas encontradas:** `asaas_transactions`, `payments`, `orders`.

---

## 3. Análise e Recomendações

### 3.1 Reutilização
- As tabelas `agent_config` e `agent_performance_metrics` podem ser aproveitadas, mas precisam de expansão para suportar multi-tenancy (atualmente não possuem `tenant_id` ou `affiliate_id`).
- A tabela `sub_agents` também deve ser auditada para verificar a arquitetura atual de sub-agentes.

### 3.2 O que falta (Fase 1)
- `agent_tenants`: Tabela central para vincular afiliados às configurações do agente.
- `agent_conversations` e `agent_messages`: Para histórico de chat.
- `agent_knowledge`: Para base de conhecimento (RAG).

### 3.3 Alertas e Conflitos
- **Segurança:** A política RLS de `agent_performance_metrics` permite acesso total a qualquer um. Deve ser restrita por tenant.
- **Nomenclatura:** Manter o padrão `agent_*` para novas tabelas conforme solicitado.
- **Assinaturas:** Necessário validar com o time onde o "Status de Assinatura Ativa" é verificado (se é um campo no `affiliates` ou se consulta transações do Asaas em tempo real).
