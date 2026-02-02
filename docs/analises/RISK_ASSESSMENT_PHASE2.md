# Risk Assessment: Fase 2 (Integração de Produtos)

**Data:** 01/02/2026
**Fase:** Implementação de `ProductService` e `SalesSkill`.

---

## 🚀 Riscos Identificados

### 1. Acoplamento de Schema (Médio)
*   **Problema:** O `ProductService` vai assumir que existe uma tabela `products` com colunas específicas (`name`, `price`, `description`).
*   **Cenário Real:** Se no futuro integrarmos com Shopify/WooCommerce, os dados não estarão nessa tabela.
*   **Mitigação:** Implementar `ProductService` como uma **Interface** (`IProductService`), onde a implementação padrão lê do Supabase, mas futuras implementações podem ler de APIs externas.

### 2. Estouro de Contexto do LLM (Alto)
*   **Problema:** Se um tenant tiver 5.000 produtos e o filtro for genérico ("quero algo legal"), injetar tudo no prompt quebrará o agente (Token Limit) ou causará alucinação.
*   **Mitigação:**
    *   Limitar hardcoded: `LIMIT 5` produtos no `get_products`.
    *   O LLM deve ser instruído a **pedir mais filtros** se a busca retornar muitos resultados.

### 3. Latência (Médio)
*   **Problema:** A busca vetorial (se usada) ou SQL + formatação de prompt adiciona tempo.
*   **Mitigação:** Usar índices no banco (`tenant_id`, `price`). Manter a query simples por enquanto (LIKE/ILIKE) antes de partir para Vector Search (PgVector).

### 4. Segurança de Dados (Crítico)
*   **Problema:** Vazamento de dados entre Tenants (Tenant A ver produtos do Tenant B).
*   **Mitigação:**
    *   **RLS (Row Level Security):** Garantir que o RLS do Supabase esteja ativo.
    *   **Backend Enforced:** O `ProductService` deve OBRIGATORIAMENTE receber `tenant_id` e incluí-lo no `WHERE`. Nunca confiar apenas no frontend.

### 5. Frontend Break (Baixo)
*   **Problema:** O Frontend atual não espera receber `products_recommended`. Pode ignorar ou quebrar se o payload JSON mudar formato.
*   **Mitigação:** O campo `products_recommended` será opcional no AgentState. O frontend atual apenas ignorará o campo até ser atualizado.

---

## 🛡️ Estratégia de Mitigação (Ações Imediatas)

1.  **Validação de Schema:** Antes de codar, verificar se a tabela `products` já existe e se atende aos requisitos.
2.  **Interface Agnostic:** Criar `ProductService` desacoplado.
3.  **Limite de Segurança:** Hardcode `TOP_k=5` na busca de produtos.
4.  **Teste de Isolamento:** Criar caso de teste específico verificando vazamento de tenant.

Posso prosseguir com essas mitigações em mente?
