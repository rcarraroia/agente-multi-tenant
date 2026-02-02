# Cronograma e Fases do Projeto - Agente Multi-Tenant

## 1. Visão Geral

Este documento detalha o planejamento estratégico do projeto Agente Multi-Tenant. O desenvolvimento seguirá uma metodologia **iterativa e incremental**, garantindo que cada fase entregue um conjunto de funcionalidades prontas para teste e validação.

*   **Princípio:** Cada fase deve entregar valor funcional tangível.
*   **Critério de Conclusão:** Uma fase é considerada concluída somente após a validação bem-suceda de todos os seus itens de entrega e aprovação técnica.

---

## 2. Detalhamento por Fase

### FASE 1 - BACKEND CORE
**Objetivo:** Fundação tecnológica do sistema, estabelecendo o isolamento multi-tenant e o cérebro da IA.

#### 📦 Entregas
*   **Multi-tenancy:** Sistema de isolamento de dados via `tenant_id` em todas as rotas e tabelas.
*   **Base de Dados:** Implementação do schema no Supabase (configurado com RLS e tabelas `multi_agent_*`).
*   **Motor de IA:** Multi-Agente básico utilizando LangChain e LangGraph para orquestração.
*   **Integração Handoff:** API de conexão com Chatwoot para transferência de atendimento.
*   **Gestão de Conversas:** APIs para listar, enviar e atribuir mensagens.
*   **Recepção de Dados:** Webhook para captura de mensagens recebidas.

#### 🔗 Dependências
*   Nenhuma (Fase de inicialização).

#### ✅ Validação de Conclusão
*   [x] Um novo tenant pode ser provisionado e os dados permanecem isolados.
*   [x] O multi-agente responde corretamente a perguntas básicas da base de conhecimento.
*   [x] É possível transferir uma conversa ativa para o Chatwoot via API.

---

### FASE 1.5 - SISTEMA DE APRENDIZADO (SICC) ✅ (100% CONCLUÍDA)
**Objetivo:** Implementar captura inteligente de contexto e aprendizado contínuo

#### 📦 Entregas
*   **Sistema de Captura de Aprendizados**:
    *   Tabela `multi_agent_learnings` (padrões identificados) -> Renomeado para `sicc_learning_logs` para consistência 2.0
    *   Tabela `multi_agent_feedback` (avaliação de respostas) -> Integrado em `sicc_metrics` e `sicc_behavior_patterns`
    *   Captura automática de interações bem-sucedidas
*   **SICC (Sistema Inteligente de Captura de Contexto)**:
    *   Extração de padrões das conversas
    *   Identificação de perguntas recorrentes
    *   Melhoria contínua da base de conhecimento
*   **Consolidação Multi-Tenant**:
    *   Aprendizados individuais por tenant
    *   Promoção de padrões validados para conhecimento global
    *   Painel admin para revisar aprendizados (Back-end pronto)
*   **RAG Enriquecido**:
    *   Integração de learnings no sistema de busca
    *   Priorização de padrões aprendidos vs conhecimento estático
    *   **Nó de Reflexão** para auto-correção de respostas

#### 🔗 Dependências
*   [x] **Fase 1 Concluída:** Necessita do Motor IA funcionando e gerando conversas reais.
*   [x] **Piloto Executado:** Mínimo de 2-4 semanas de dados reais coletados (3-5 afiliados).

#### ✅ Validação de Conclusão
*   [x] Sistema captura padrões de conversas bem-sucedidas.
*   [x] Admin pode revisar e aprovar aprendizados (Estrutura de dados pronta).
*   [x] RAG utiliza learnings nas buscas (Busca Híbrida implementada).
*   [x] Aprendizados de um tenant podem ser promovidos para global.
*   [x] Métricas mostram melhoria na taxa de acerto do agente (Nó de Reflexão validado).

---

### FASE 2 - INTEGRAÇÕES
**Objetivo:** Conectar o sistema ao mundo externo e ao ecossistema Slim Quality.

#### 📦 Entregas
*   **WhatsApp:** Integração completa com a Evolution API.
*   **Slim Security:** Autenticação via JWT compartilhada com o sistema Slim Quality.
*   **Financeiro Automatizado:** Webhook do Asaas para gestão de ciclos de vida do tenant (Ativação/Suspensão).
*   **Assinaturas Recorrentes:** Configuração de assinatura recorrente no Asaas (primeira do sistema).
*   **Validação de Negócio:** Camada de middleware para verificar assinaturas ativas.
*   **Sincronização:** Consumo direto das tabelas de afiliados e assinaturas do Slim Quality.

#### 🔗 Dependências
*   **Fase 1 Concluída:** Necessita do Backend Core e estrutura de banco estáveis.

#### 📄 Especificação Detalhada
*   **Tasks:** [.spec/fase-2-ativacao-multi-tenant/tasks.md](file:///.spec/fase-2-ativacao-multi-tenant/tasks.md)
*   **Design:** [.spec/fase-2-ativacao-multi-tenant/design.md](file:///.spec/fase-2-ativacao-multi-tenant/design.md)
*   **Requirements:** [.spec/fase-2-ativacao-multi-tenant/requirements.md](file:///.spec/fase-2-ativacao-multi-tenant/requirements.md)

#### ✅ Validação de Conclusão
*   [x] Mensagens enviadas via WhatsApp aparecem no backend e recebem resposta da IA. (Infraestrutura de ponte pronta)
*   [x] Autenticação JWT compartilhada implementada (SUPABASE_JWT_SECRET configurado)
*   [x] Provisionamento automático de tenant implementado (função `provisionMultiAgentTenant`)
*   [x] Webhook Asaas para ciclo de vida implementado (`webhooks_asaas.py`)
*   [x] Configuração de assinatura recorrente no Asaas (`asaas_service.py`)
*   [ ] **Deploy Edge Function `process-split`** (pendente - requer autenticação CLI ou deploy manual)
*   [ ] **Deploy Backend Agente na VPS** (pendente - aguardando conclusão de fases seguintes)
*   [ ] Login de afiliado realizado com sucesso usando credenciais existentes (pendente deploy)
*   [x] Confirmação de pagamento no Asaas ativa automaticamente as funcionalidades do multi-agente (Lógica pronta no Webhook)

---

### FASE 2.5 - ARQUITETURA DE SKILLS E QUALIDADE ✅ (100% CONCLUÍDA)
**Objetivo:** Modularizar as capacidades do agente e garantir precisão nas vendas.

#### 📦 Entregas
*   **Arquitetura de Business Skills:** Sistema plugável (`BaseSkill`, `Registry`, `Router`).
*   **Integração Catálogo Global:** Consumo direto da tabela `public.products` da Slim Quality.
*   **Product Service:** Camada de serviço com tratamento de precisão decimal para preços.
*   **Skill de Vendas:** Módulo especializado para oferta de produtos e negociação de parcelamento.
*   **Nó Supervisor:** Camada de auditoria que valida preços e evita alucinações antes da resposta final.
*   **Loop de Auto-Correção:** Capacidade do agente de corrigir a própria resposta baseada no feedback do Supervisor.

#### 🔗 Dependências
*   [x] **Fase 1 Concluída:** Necessita do Motor IA (LangGraph).
*   [x] **Fase 2 (Parcial):** Necessita de conexão com banco de dados Slim Quality.

#### ✅ Validação de Conclusão
*   [x] Agente identifica intenção de compra e alterna para a Sales Skill.
*   [x] Preços citados pelo agente são validados contra o banco pelo Supervisor.
*   [x] O catálogo de produtos é lido em tempo real sem duplicação de dados.

---

### FASE 3 - CRM KANBAN (BACKEND) ✅ (100% CONCLUÍDA)
**Objetivo:** Implementar a lógica de gestão visual de leads e oportunidades.

#### 📦 Entregas
*   **Estrutura de Funil:** Tabelas e lógica para múltiplos funis e etapas personalizáveis.
*   **APIs CRM:** Endpoints de CRUD para funis e etapas.
*   **Lógica de Movimentação:** Processamento de mudança de estágio com registro de histórico.
*   **Automação de Leads:** Lógica para transformar novas conversas em cards automáticos no primeiro estágio.

#### 🔗 Dependências
*   **Fase 1 Concluída:** Necessita da estrutura de conversas pronta.

#### 📄 Especificação Detalhada
*   **Tasks:** [.spec/fase-3-crm-kanban/tasks.md](file:///.spec/fase-3-crm-kanban/tasks.md)
*   **Design:** [.spec/fase-3-crm-kanban/design.md](file:///.spec/fase-3-crm-kanban/design.md)
*   **Requirements:** [.spec/fase-3-crm-kanban/requirements.md](file:///.spec/fase-3-crm-kanban/requirements.md)

#### ✅ Validação de Conclusão
*   [x] Criação e edição de funis e etapas via API funcionando.
*   [x] Histórico de movimentação de um lead registrado corretamente no banco.
*   [x] Novas conversas aparecem vinculadas ao estágio inicial configurado.

---

### FASE 4 - FRONTEND
**Objetivo:** Construção da interface do usuário (UI) para os afiliados.

#### 📦 Entregas
*   **Portal do Afiliado:** Estrutura base seguindo a identidade visual do Slim Quality.
*   **Dashboard "Meu Multi-Agente":** Visão geral do status do agente e conexões.
*   **Central de Mensagens:** Interface de chat em tempo real com lista de conversas.
*   **Kanban Board:** Interface visual com suporte a drag-and-drop para movimentação de cards.
*   **Configurações:** Painéis para ajuste de personalidade da IA e chaves de API.
*   **Checkout:** Interface de assinatura integrada ao fluxo financeiro.

#### 🔗 Dependências
*   **Fases 1, 2 e 3 Concluídas:** Necessita de todas as APIs de negócio prontas.

#### ✅ Validação de Conclusão
*   [ ] O afiliado consegue visualizar e responder chats pelo painel.
*   [ ] A movimentação de cards no Kanban reflete instantaneamente no banco de dados.
*   [ ] O fluxo completo de login até a configuração do agente está funcional.

---

### FASE 5 - DASHBOARD E FECHAMENTO
**Objetivo:** Refinamento técnico, métricas de performance e preparação para produção.

#### 📦 Entregas
*   **Analytics:** Dashboard completo com KPIs (leads, taxas de conversão, volume de mensagens).
*   **Relatórios:** Visualizações gráficas de performance por período.
*   **QA & Testes:** Execução de testes end-to-end (E2E) e stress tests.
*   **DevOps:** Documentação completa de deploy e infraestrutura.
*   **Estabilização:** Correção de bugs menores identificados nas fases anteriores.

#### 🔗 Dependências
*   **Fase 4 Concluída:** Sistema completo deve estar disponível para uso.

#### ✅ Validação de Conclusão
*   [ ] Os gráficos de métricas batem com os dados reais do banco.
*   [ ] O sistema suporta um piloto com 3-5 afiliados sem degradação de performance.
*   [ ] Documentação técnica de entrega finalizada.

---

### FASE 6 - SEGURANÇA GLOBAL E GUARDRAILS (FUTURO / PÓS-PILOTO) 🚧
**Objetivo:** Implementar filtros globais de segurança e proteção de marca.

#### 📦 Entregas
*   **Global Guardrails:** Implementação de biblioteca (ex: NeMo Guardrails) para filtros de toxicidade e injeção de prompt.
*   **Brand Protection:** Filtros para evitar citações a concorrentes ou assuntos fora do escopo.
*   **Análise de Sentimento:** Monitoramento de frustração do usuário para handoff preventivo.

#### 🔗 Dependências
*   [ ] **Fase 5 Concluída:** Estabilização do sistema em produção.

---

### FASE 7 - INTEGRAÇÃO GOOGLE (FUTURO / PÓS-ESTABILIZAÇÃO) 🚧
**Objetivo:** Permitir agendamento automático de reuniões via agenda e Meet.

#### 📦 Entregas
*   **Google OAuth:** Integração para conexão segura de contas Google por tenant.
*   **Google Calendar Skill:** Habilidade do agente para verificar disponibilidade e criar eventos.
*   **Google Meet Integration:** Geração automática de links de videoconferência.

#### 🔗 Dependências
*   [ ] **Fase 4 e 5 Concluídas:** Sistema operacional e interface administrativa pronta.

---

## 3. Dependências Críticas

> [!IMPORTANT]
> **Fluxo de Desenvolvimento:**
> - **Sequencial obrigatório:** Fase 1 → Piloto (2-4 semanas) → Fase 1.5
> - **Sequencial Obrigatório:** Fase 1 → Fase 2 → Fase 4 (Flow de Atendimento)
> - **Sequencial Obrigatório:** Fase 1 → Fase 3 (Flow de CRM)
> - **Paralelismo Permitido:** As Fases 2 (Integrações) e 3 (CRM) podem ser desenvolvidas simultaneamente após a conclusão da Fase 1.

---

## 4. Critérios de Qualidade

| Item | Requisito |
| :--- | :--- |
| **Testes** | Mínimo de 80% de cobertura no Core; Testes de integração em Webhooks. |
| **Documentação** | Todos os endpoints documentados; Comentários em funções complexas. |
| **Code Review** | Validação obrigatória de isolamento de tenant em cada PR. |

---

## 5. Riscos e Mitigações

*   **Fase 1 (Multi-tenancy):** Risco de vazamento de dados. **Mitigação:** Implementar RLS estrito e testes automatizados de tentativa de acesso cross-tenant.
*   **Fase 2 (Integrações):** Downtime ou mudanças em APIs terceiras (Evolution/Chatwoot). **Mitigação:** Uso de adapters e tratamento rigoroso de errors/retries.
*   **Fase 4 (Tempo Real):** Gargalos em Websockets com muitos usuários ativos. **Mitigação:** Escalabilidade horizontal das instâncias do backend e Redis pub/sub.

---
