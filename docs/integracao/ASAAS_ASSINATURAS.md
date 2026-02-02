# Integração Asaas - Assinaturas Recorrentes

Este documento detalha o mapeamento técnico da integração com o Asaas para o modelo de assinaturas recorrentes do Agente Multi-Tenant.

## 1. Endpoints API (V3)

### 1.1 Criar Assinatura
- **Endpoint:** `POST /v3/subscriptions`
- **Descrição:** Cria um agendamento de cobranças recorrentes.
- **Payload Relevante:**
```json
{
  "customer": "customer_id",
  "billingType": "CREDIT_CARD", // OU PIX, BOLETO
  "value": 197.00,
  "nextDueDate": "2026-02-21",
  "cycle": "MONTHLY",
  "description": "Assinatura Agente IA Multi-Tenant",
  "externalReference": "tenant_id",
  "split": [
    {
      "walletId": "wallet_id_afiliado",
      "percentualValue": 30.00
    }
  ]
}
```

### 1.2 Cancelar Assinatura
- **Endpoint:** `DELETE /v3/subscriptions/{id}`
- **Efeito:** Interrompe a geração de novas cobranças. As já geradas permanecem pendentes a menos que `updatePendingPayments: true` seja enviado (não recomendado por padrão).

### 1.3 Consultar Assinatura
- **Endpoint:** `GET /v3/subscriptions/{id}`
- **Retorno:** Status da assinatura (`ACTIVE`, `EXPIRED`, etc).

---

## 2. Webhooks

O Asaas dispara webhooks tanto para a **Assinatura** (entidade pai) quanto para as **Cobranças** (entidade filha).

### 2.1 Eventos de Assinatura
- `SUBSCRIPTION_CREATED`: Confirmar criação no banco.
- `SUBSCRIPTION_DELETED`: Marcar como cancelada internamente.

### 2.2 Eventos de Pagamento (Charge)
Estes eventos devem ser usados para controlar o acesso ao sistema:
- `PAYMENT_CONFIRMED`: Ativa/Mantém acesso do tenant. Atualiza `next_due_date`.
- `PAYMENT_OVERDUE`: Pagamento atrasado. Bloqueia acesso após X dias (conforme regra de negócio).

---

## 3. Ciclo de Vida e Regras de Bloqueio

| Status Asaas | Estado Interno | Acesso ao Agente | Ação Recomendada |
| :--- | :--- | :--- | :--- |
| `ACTIVE` | Ativa | Liberado | Operação normal. |
| `OVERDUE` | Inadimplente | **Bloqueado** | Redirecionar para tela de pagamento. |
| `CANCELED` | Cancelada | **Bloqueado** | Modo leitura para conversas antigas. |
| `EXPIRED` | Expirada | **Bloqueado** | Solicitar nova assinatura. |

---

## 4. Split de Comissões

O Asaas suporta split recorrente. 
- Ao definir o `split` na criação da assinatura (`/v3/subscriptions`), todas as cobranças mensais automáticas já nascem com o split configurado.
- Isso dispensa o backend de ter que processar o split manualmente a cada mês, aumentando a segurança e reduzindo erros de cálculo.

---

## 5. Schema da Tabela `multi_agent_subscriptions`

Esta tabela vincula o sistema Slim Quality à entidade de assinatura do Asaas.

| Campo | Tipo | Descrição |
| :--- | :--- | :--- |
| `id` | uuid (PK) | Identificador interno. |
| `tenant_id` | uuid (FK) | Relacionamento com `multi_agent_tenants`. |
| `affiliate_id` | uuid (FK) | Relacionamento com `affiliates` (Legado). |
| `asaas_subscription_id` | text | ID retornado pelo Asaas (`sub_...`). |
| `status` | text | `active`, `overdue`, `canceled`, `expired`. |
| `plan_value_cents` | integer | Valor em centavos para evitar erros de float. |
| `next_due_date` | date | Próxima data de cobrança prevista. |
| `billing_type` | text | `CREDIT_CARD`, `BOLETO`, `PIX`. |
| `created_at` | timestamptz | Data de criação. |
| `updated_at` | timestamptz | Data da última alteração de status. |

---

## 6. Fluxos Completos

### 6.1 Primeira Ativação
1. Frontend chama API `POST /multi-agent/subscribe`.
2. Backend cria Customer no Asaas (usando `asaasService`).
3. Backend cria Assinatura no Asaas com `split` configurado.
4. Backend salva registro em `multi_agent_subscriptions` como `pending`.
5. Usuário paga a primeira parcela.
6. Webhook `PAYMENT_CONFIRMED` é recebido.
7. Backend ativa o `multi_agent_tenants`.

### 6.2 Renovação Mensal
1. Asaas gera nova cobrança e envia link por e-mail/notificação.
2. Usuário paga.
3. Webhook `PAYMENT_CONFIRMED` é recebido.
4. Backend localiza `multi_agent_subscriptions` pelo `subscription_id`.
5. Backend atualiza `next_due_date`.

---

## 7. Integração com Sistema Existente

### Reuso de Código
- **`asaas.service.ts`**: Adicionar método `createSubscription(data)`.
- **`asaas-webhook.ts`**: 
    - Atualmente o webhook em `slim-quality` foca em `orders`.
    - **Ação:** Devemos expandir o handler para verificar se o `payment.subscription` existe.
    - Se existir, a lógica deve priorizar o fluxo do Multi-Agente em vez de fluxos de produtos físicos.

### Diferenciação
O Asaas envia o campo `subscription` no payload de pagamento quando este pertence a uma recorrência. Usaremos este campo como discriminador.

---

## 8. Exemplo de Implementação Webhook (Draft)

```typescript
// No handler de PAYMENT_CONFIRMED
if (payment.subscription) {
  // 1. Localizar multi_agent_subscriptions
  // 2. Ativar/Manter Tenant
  // 3. Atualizar datas
} else {
  // Fluxo legado de venda única
}
```
