# Arquitetura do Sistema - Agente Multi-Tenant

## 1. Visão Geral do Sistema

*   **Propósito:** Agente de Inteligência Artificial multi-tenant projetado especificamente para os afiliados do sistema Slim Quality.
*   **Modelo de Negócio:** Software as a Service (SaaS) com modalidade de assinatura mensal recorrente.
*   **Convivência:** Este sistema opera em paralelo ao atual painel administrativo do Slim Quality, coexistindo com as automações e agentes já existentes, mas focando na escala de múltiplos tenants (afiliados).
*   **Diferencial Estratégico:** Base de conhecimento compartilhada entre todos os tenants, combinada com contextos específicos de cada afiliado, permitindo um atendimento automatizado altamente preciso com suporte a transição fluida (handoff) para atendimento humano.

---

## 2. Stack Tecnológica

### Backend
*   **Framework:** FastAPI (Python) para APIs de alta performance.
*   **Orquestração de IA:** LangChain e LangGraph para a lógica de grafos do agente.
*   **Processamento de Voz:** 
    *   Whisper (transcrição de áudio para texto).
    *   TTS (Text-to-Speech para respostas em áudio).
*   **Protocolo MCP:**
    *   Supabase MCP Server (acesso direto ao banco).
    *   MCP Gateway (orquestração de ferramentas).
*   **Memória:** Redis para armazenamento de sessões conversacionais e cache.
*   **Banco de Dados:** Supabase (PostgreSQL) para persistência de dados.

### Frontend
*   **Framework:** Next.js / React (Versão definitiva a ser confirmada).
*   **UI/UX:** shadcn/ui para componentes e Tailwind CSS para estilização premium.

### Integrações
*   **Canais:** Evolution API para integração direta com WhatsApp.
*   **Handoff:** Chatwoot para interface de atendimento humano.
*   **Financeiro:** Asaas para gestão de pagamentos e assinaturas.
*   **Ecosystem:** Integração profunda com o sistema Slim Quality existente (Autenticação, Dados de Afiliados, Comissões).

---

## 3. Arquitetura Multi-Tenant

O sistema é desenhado para garantir total isolamento entre os afiliados (tenants):
*   **Isolamento de Dados:** Cada registro no banco de dados está vinculado a um `tenant_id`.
*   **Segurança:** Implementação de Row Level Security (RLS) no Supabase.
*   **Contexto de IA:** O agente utiliza uma base de conhecimento global (conhecimento compartilhado) mesclada dinamicamente com as configurações e dados específicos do afiliado logado.

---

## 4. Módulos Principais

### 4.1 Autenticação
*   Reutilização do sistema de autenticação do Slim Quality.
*   Compartilhamento de sessões via JWT.
*   Middleware de validação de assinatura ativa antes de liberar o processamento do agente.

### 4.2 Agente IA
*   Processamento assíncrono de mensagens do WhatsApp.
*   Raciocínio baseado em recuperação de conhecimento (RAG).
*   Lógica de decisão inteligente para identificar quando o cliente precisa de intervenção humana.

### 4.3 Multiatendimento WhatsApp
*   Interface em tempo real para visualização de conversas.
*   Sistema de filas: "Minhas conversas" vs "Fila do time".
*   Suporte a arquivos multimídia (Texto, Imagem, Vídeo, Áudio).
*   Push notifications para novos eventos.

### 4.4 CRM com Funil Kanban
*   Gerenciamento visual de leads através de colunas drag-and-drop.
*   Conversão automática: Novas conversas iniciam como cards no primeiro estágio do funil.
*   Histórico completo de transições entre etapas para análise de vendas.

### 4.5 Handoff IA ↔ Humano
*   Integração bidirecional com Chatwoot.
*   Transferência automática de contexto (resumo da conversa pela IA) para o atendente.
*   Mecanismo de "devolução" para a IA após a resolução humana.

### 4.6 Dashboard e Métricas
*   Analytics centralizado: Conversas, leads, conversões e faturamento.
*   Visualizações gráficas para acompanhamento de performance do afiliado.

### 4.7 Gestão de Assinatura
*   Fluxo de checkout integrado via Asaas.
*   **Importante:** Este é o primeiro produto do Slim Quality vendido por assinatura recorrente. A integração com Asaas será configurada especificamente para este modelo de negócio.
*   Automação de comissões para a rede de afiliados Slim Quality.
*   Bloqueio automático de recursos em caso de inadimplência.

---

## 5. Estrutura do Banco de Dados

### Tabelas Específicas (Novas - Prefixo `multi_agent_*`)
*   `multi_agent_tenants`: Configurações de branding, personalidade e chaves de API por afiliado.
*   `multi_agent_conversations`: Metadados das sessões de chat.
*   `multi_agent_messages`: Log completo de interações.
*   `multi_agent_knowledge`: Documentos e snippets de conhecimento (compartilhados e específicos).
*   `multi_agent_funnels`: Definições de funis de vendas.
*   `multi_agent_funnel_stages`: Etapas configuráveis para o Kanban.
*   `multi_agent_handoffs`: Registro de transferências para o Chatwoot.
*   `multi_agent_subscriptions`: Controle de assinaturas recorrentes no Asaas.

### Sistema Admin Existente (Convivência)
O banco de dados Slim Quality já possui tabelas com prefixo `agent_*` que pertencem ao sistema de agente único do painel admin e serão mantidas intactas:
- `agent_config`
- `agent_performance_metrics`
- `sub_agents`

O novo sistema multi-tenant utiliza o prefixo **`multi_agent_*`** para garantir total separação e evitar conflitos.

**Estratégia de Migração Futura:**
Após validação completa do sistema multi-tenant, o menu antigo "Meu Agente" será removido do painel admin. As tabelas `agent_*` antigas podem ser mantidas para histórico ou removidas conforme necessidade.

### Tabelas Integradas (Reuso Slim Quality)
> [!IMPORTANT]
> **Princípio de Reuso:** Não haverá duplicação de dados. O sistema deve consumir diretamente as tabelas existentes do Slim Quality através de consultas externas ou links de banco.

*   **`affiliates`**: Fonte única para identificação do proprietário do tenant.
*   **`subscriptions`**: Controle centralizado de vigência do plano.
*   **`commissions`**: Lançamentos financeiros gerados pela assinatura do agente.

---

## 6. APIs e Endpoints (Grupos Funcionais)

*   **Grupo Multi-Agente:** Processamento de mensagens WhatsApp, busca de conhecimento e decisões de handoff.
*   **Grupo Conversas:** Listagem, detalhes, envio de mensagens e atribuição de conversas.
*   **Grupo CRM/Funil:** Gestão de funis, etapas, movimentação de cards e histórico.
*   **Grupo Handoff:** Solicitação, status e resolução de transferências humanas.
*   **Grupo Dashboard:** Coleta de métricas e dados para análise.
*   **Grupo Configurações:** Ajustes de tenant e conexão com serviços externos (WhatsApp).

---

## 7. Integrações Externas

| Serviço | Função Principal | Mecanismo |
| :--- | :--- | :--- |
| **Evolution API** | Mensageria WhatsApp | Webhooks / REST |
| **Chatwoot** | Atendimento Humano | API / Webhooks |
| **Asaas** | Pagamentos e Assinaturas | Webhooks |
| **Slim Quality** | Core Business e Auth | API Interna / Shared DB |

---

## 8. Fluxos de Trabalho Principais

1.  **Onboarding:** Inscrição → Pagamento (Asaas) → Ativação de Provisionamento → Conexão WhatsApp.
2.  **Atendimento:** Mensagem Recebida → IA Processa → IA Responde OU IA Transfere para Humano.
3.  **Vendas:** Conversa → Card Criado no Kanban → Movimentação pela Jornada do Cliente.

---

## 9. Segurança e Performance

*   **Segurança:** JWT, RLS (PostgreSQL), Rate Limiting, Sanitização de Dados.
*   **Performance:** Redis para persistência de estado do LangGraph, Websockets para UI real-time, CDN para assets frontend.

---

## 10. Cronograma de Implementação

| Fase | Descrição |
| :--- | :--- |
| **Fase 1 - Backend Core** | Multi-tenancy, Isolamento, Multi-Agente IA básico, API Handoff e Chat. |
| **Fase 1.5 - SICC (Aprendizado)** | Sistema de Captura de Contexto, Learnings Multi-Tenant, RAG Enriquecido. |

| **Fase 2 - Integrações** | Evolution API (WhatsApp), Slim Quality Auth/Assinatura, Webhooks Asaas. |
| **Fase 3 - CRM Kanban** | Definição de Funis, Etapas, Drag-and-Drop e Histórico de Movimentação. |
| **Fase 4 - Frontend** | Painel do Afiliado, Interface de Chat e Kanban Board. |
| **Fase 5 - Fechamento** | Dashboards, Métricas e Ajustes Finais baseados em testes. |
