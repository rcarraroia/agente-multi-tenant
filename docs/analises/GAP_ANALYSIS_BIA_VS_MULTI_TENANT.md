# Gap Analysis: Agente Bia (Slim Quality) vs Agente Multi-tenant

**Data:** 01/02/2026
**Responsável:** Antigravity (via Brainstorming Analysis)
**Contexto:** Verificação de funcionalidades e UX/UI implementadas no agente Bia (Slim Quality) que ainda não foram portadas para o sistema Multi-tenant.

---

## 1. Visão Geral

O agente **Bia (Slim Quality)** possui uma arquitetura sofisticada baseada em sub-agentes especializados (`discovery`, `sales`, `support`), integração profunda com catálogo de produtos (Supabase) e um fluxo de aprovação via Supervisor.

O **Agente Multi-tenant** atual opera em um modelo mais simplificado ("Monolítico"), onde a maioria das interações converge para um único nó de geração (`generate_response`), apoiado por RAG e Reflexão SICC, mas sem a especialização de tarefas e sem capacidades de venda ativa (catálogo de produtos).

---

## 2. Funcionalidades Faltantes (GAP Tecnológico)

### 🔴 Crítico: Especialização de Sub-agentes
| Feature | Bia (Slim Quality) | Multi-tenant | Impacto |
|---------|--------------------|--------------|---------|
| **Arquitetura** | **Grafo com Sub-agentes**: Nós explícitos para Vendas, Suporte e Descoberta. | **Grafo Linear**: Centralizado em `generate_response` + `rag_search`. | O Multi-tenant trata vendas e suporte da mesma forma, perdendo a "personalidade" de vendedor. |
| **Roteamento** | Roteamento baseado em intenção para nós específicos (`sicc_lookup` -> `sales`/`support`). | Roteamento apenas para RAG ou Geração (`classify_intent`). | Menor precisão no tratamento de fluxos complexos. |

### 🔴 Crítico: Capacidades de Venda (Sales Node)
| Feature | Bia (Slim Quality) | Multi-tenant | Impacto |
|---------|--------------------|--------------|---------|
| **Integração de Produtos** | Busca ativa no Supabase (`get_products`) com filtros (preço, problema de saúde). | ❌ Inexistente. | O agente não sabe o que vende. Alucina ou dá respostas genéricas. |
| **Formatação de Oferta** | Formata produtos tecnicamente (preço, firmeza, tecnologias) e injeta no prompt. | ❌ Inexistente. | Não consegue apresentar produtos de forma estruturada. |
| **Negociação** | Lógica de negociação e parcelamento hardcoded no prompt do nó de vendas. | ❌ Inexistente. | Perde oportunidade de conversão. |

### 🟡 Importante: Fluxo de Supervisão e Aprendizado
| Feature | Bia (Slim Quality) | Multi-tenant | Impacto |
|---------|--------------------|--------------|---------|
| **Supervisor** | Nó `supervisor_approve` garante qualidade antes do fim. | ❌ Inexistente (Substituído parcialmente por `sicc_reflection`). | Menor garantia de qualidade em respostas críticas. |
| **Ciclo SICC** | Estrutura explícita `Lookup -> SubAgent -> Learn`. | Estrutura `Retrieve -> Generate -> Reflect`. | O aprendizado no Multi-tenant é um efeito colateral, não um passo estrutural do grafo (embora exista `sicc_reflection`). |

---

## 3. Interfaces UX/UI Faltantes (GAP de Interface)

A análise do backend revela lacunas diretas no frontend, pois o estado do agente (`AgentState`) não transporta os dados necessários para a UI rica.

### 🔴 Crítico: Cards e Carrossel de Produtos
- **Bia (Slim):** O nó `sales.py` retorna `products_recommended` no estado. Isso permite que o frontend renderize:
    - Carrossel de produtos (Imagem + Nome + Preço).
    - Botões de "Comprar" ou "Ver Detalhes".
- **Multi-tenant:** O estado possui apenas `final_response` (texto).
    - **Resultado:** O frontend só consegue exibir texto corrido (Markdown). Não há suporte para interfaces ricas de e-commerce.

### 🟡 Importante: Feedback Visual de Processamento
- **Bia (Slim):** A presença de nós distintos (`sicc_lookup`, `sales`, `supervisor`) permite feedback granular na UI ("Buscando produtos...", "Consultando supervisor...").
- **Multi-tenant:** Como o fluxo é curto (`RAG -> Generate`), o feedback é genérico ("Digitando...").

---

## 4. Análise de Código Comparativa

### Estrutura do Grafo (`builder.py` vs `graph.py`)

**Slim Quality (`builder.py`):**
```python
# Roteamento condicional para especialistas
workflow.add_conditional_edges(
    "sicc_lookup",
    route_intent,
    {
        "discovery": "discovery",
        "sales": "sales",     # <--- Nó Especialista
        "support": "support"
    }
)
# Todos convergem para aprendizado e supervisão
workflow.add_edge("sales", "sicc_learn")
workflow.add_edge("sicc_learn", "supervisor_approve")
```

**Multi-tenant (`graph.py`):**
```python
# Roteamento simples RAG vs Geração
workflow.add_conditional_edges(
    "classify",
    router_function,
    {
        "rag_search": "rag_search",
        "generate": "generate", # <--- Nó Genérico
        "check_handoff": "check_handoff"
    }
)
workflow.add_edge("rag_search", "generate")
# Falta: Sales Node, Supervisor Node, Products Integration
```

---

## 5. Recomendações (Roadmap Sugerido)

Para elevar o Agente Multi-tenant ao nível da Bia, sugerimos as seguintes implementações (seguindo o protocolo OpenSpec):

1.  **Refatoração do Grafo (Backend):**
    - Implementar `sales_node` no Multi-tenant.
    - Adicionar integração com tabela de produtos (agnóstica ao tenant).
    - Portar lógica de `sicc_learn` como nó explícito se desejado.

2.  **Atualização de Schema (Backend):**
    - Atualizar `AgentState` no Multi-tenant para incluir:
        - `products_recommended: List[Product]`
        - `lead_data: Dict` (para personalização de venda)

3.  **Atualização de Frontend (UX/UI):**
    - Implementar componentes de UI para renderizar `products_recommended` (Cards/Carrossel).
    - Melhorar indicadores de estado baseados nos novos nós do grafo.

---
*Relatório gerado via análise estática de código (Brainstorming).*
