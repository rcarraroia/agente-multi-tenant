# Análise Estratégica: Roadmap, Segurança e Arquitetura de Skills

**Data:** 01/02/2026
**Contexto:** Definição de estratégia para evolução do Agente Multi-tenant comparado ao Agente Bia.

---

## 1. Devo implementar o Roadmap sugerido (5 itens) + Guardrails + Fine-tuning?

### A. O Roadmap de GAPs (Prioridade: 🔥 IMEDIATA)
**Veredito:** **SIM, OBRIGATÓRIO.**
As 5 recomendações do relatório anterior (especialmente os Nós de Vendas e Integração de Produtos) são **funcionais**.
- **Por que:** Sem isso, seu agente multi-tenant é apenas um "chatbot genérico". Ele não consegue vender produtos, que é o core business.
- **Risco de não fazer:** O produto não tem valor comercial para os tenants (lojas).

### B. Guardrails (Prioridade: 🚀 ALTA / SPRINT SEGUINTE)
**Veredito:** **SIM, RECOMENDADO.**
Para um sistema **Multi-tenant Saas**, segurança não é opcional.
- **Por que:** Se o agente de um tenant falar besteira (alucinar, xingar, prometer descontos impossíveis), o processso recai sobre a plataforma (você).
- **Sugestão:** Implementar `nemo-guardrails` ou validadores Pydantic rigorosos **ANTES** de escalar para muitos clientes.
- **Implementação:** Camada intermediária entre o LLM e o Usuário que verifica "Tópicos Proibidos" e "Formato de Resposta".

### C. Fine-tuning (Prioridade: 🐢 BAIXA / LONGO PRAZO)
**Veredito:** **NÃO AGORA.**
- **Por que:** Fine-tuning é caro, difícil de manter e "congela" o conhecimento.
- **Melhor Alternativa:** **SICC (RAG + Dynamic Few-Shot)**. O que você já tem (SICC) é superior ao Fine-tuning para 99% dos casos, pois permite atualizar o comportamento do agente em tempo real apenas mudando os exemplos no banco, sem re-treinar modelos.
- **Quando usar:** Apenas se o SICC falhar sistematicamente em manter o "tom de voz" ou estilo de resposta específico.

---

## 2. Análise de "Skills" (Habilidades Modulares)

Você perguntou sobre implementar "Skills". Isso é uma **excelente** estratégia para SaaS Multi-tenant.

### O que são Skills neste contexto?
Em vez de um grafo monolítico, o agente é composto por módulos plugáveis que o tenant pode ativar/desativar.
*Exemplo:* Um tenant contrata o plano "Basic" (só responde dúvidas) e outro o "Pro" (vende e agenda reuniões).

### Vantagens e Desvantagens

| | Vantagens (Pros) | Desvantagens (Cons) |
|---|---|---|
| **Comercial** | Permite **Upsell**. Você vende a skill "Agendamento" como extra. | Mais complexo de explicar o preço para o cliente. |
| **Técnico** | **Isolamento de falhas**. Se a skill de "Calculadora de Frete" quebrar, o resto do agente continua funcionando. | O **Router** (cérebro) fica mais complexo. Ele precisa saber quais skills o tenant ativo tem permissão para usar. |
| **Manutenção** | Mais fácil criar skills novas sem quebrar o código antigo. | Requer gestão de dependências rigorosa (uma skill não pode conflitar com outra). |

### Como Implementar (Sugestão Arquitetural)

Não use apenas "Prompts". Use **Tools/Functions** do LangGraph.

1.  **Tabela `tenant_skills`:** No Supabase, define quais skills o tenant pagou.
    ```json
    ["product_sales", "order_status", "schedule_meeting"]
    ```

2.  **Grafo Dinâmico (LangGraph):**
    Ao carregar o agente (`load_agent`), você injeta apenas os nós correspondentes às skills ativas.

    ```python
    # Exemplo Conceitual
    workflow = StateGraph(State)
    workflow.add_node("chat", ...) # Padrão

    if "product_sales" in tenant_skills:
        workflow.add_node("sales", sales_node)
        workflow.add_edge("router", "sales")
    
    if "schedule_meeting" in tenant_skills:
        workflow.add_node("schedule", schedule_node)
        workflow.add_edge("router", "schedule")
    ```

---

## 3. Resumo da Recomendação (Plano de Ação)

Eu sugiro a seguinte ordem de execução (Pipeline):

1.  **Fase 1: Paridade Funcional (O Roadmap GAP)**
    - Implementar `SalesNode` e Integração de Produtos no Multi-tenant.
    - *Meta:* O Multi-tenant deve vender tão bem quanto a Bia.

2.  **Fase 2: Arquitetura de Skills (Refatoração)**
    - Transformar o `SalesNode` em uma "Skill" plugável.
    - Criar o sistema de verificação de features do tenant no grafo.
    - *Meta:* Poder ligar/desligar vendas por configuração no banco.

3.  **Fase 3: Segurança (Guardrails)**
    - Adicionar camada de validação de saída nas Skills críticas.
    - *Meta:* Garantir que ninguém consiga fazer o agente vender um produto por R$ 0,00.

**O que NÃO fazer agora:** Fine-tuning. Foque em melhorar o SICC (Few-Shot).

Posso criar os tickets no `tasks.md` para começar a Fase 1 (Paridade Funcional)?
