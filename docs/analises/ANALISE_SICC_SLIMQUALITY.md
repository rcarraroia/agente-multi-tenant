# Relatório de Análise Técnica: Sistema SICC (Slim Quality)

Este documento detalha a arquitetura, o banco de dados e os processos do **Sistema de Inteligência Corporativa Contínua (SICC)** implementado no projeto `slim-quality`, servindo como referência para a replicação no `agente-multi-tenant`.

## 1. Arquitetura de Software

O SICC é um sistema modular escrito em Python, orquestrado pelo `SICCService`. Ele se divide nos seguintes sub-serviços:

| Serviço | Responsabilidade |
|---------|------------------|
| **SICCService** | Orquestrador principal. Gerencia o início/fim das conversas e a integração entre os módulos. |
| **LearningService** | Analisa conversas finalizadas para detectar padrões de resposta, workflow e preferências. |
| **BehaviorService** | Identifica padrões aplicáveis em tempo real e adapta as respostas do agente. |
| **MemoryService** | Gerencia memórias vetoriais (RAG) usando pgvector e embeddings locais. |
| **MetricsService** | Coleta dados de performance, taxa de sucesso e evolução da inteligência. |
| **SupervisorService** | Avalia aprendizados sugeridos e aprova automaticamente padrões com alta confiança. |
| **AsyncProcessor** | Executa tarefas pesadas (como geração de embeddings e análise de padrões) em segundo plano. |

## 2. Estrutura do Banco de Dados (Supabase/PostgreSQL)

O sistema utiliza a extensão `pgvector` para busca semântica. As tabelas principais são:

### Tabelas Core
- `memory_chunks`: Armazena fragmentos de conversas vetorizados (384 dimensões).
- `behavior_patterns`: Repositório de padrões aprovados (trigger -> template).
- `learning_logs`: Fila de novos aprendizados aguardando aprovação (status: `pending`, `approved`, `rejected`).
- `performance_metrics`: Registros de eficácia, tempo de resposta e uso de padrões.
- `sub_agents`: Definição de personas/agentes especializados (Ex: Vendas, Suporte).

### Funções SQL (RPC)
- `search_similar_memories`: Busca vetorial pura.
- `search_memories_hybrid`: Busca combinando vetores e busca textual (Full Text Search em Português).
- `cleanup_memories_intelligent`: Limpeza automática baseada em relevância e idade.
- `update_memory_relevance`: Mecanismo de "boost" que aumenta a importância de memórias frequentemente usadas.

## 3. Fluxo de Funcionamento

### Processamento de Mensagem (Tempo Real)
1. **Contexto:** Recupera histórico do cliente e memórias relevantes da `memory_chunks`.
2. **Padrões:** `BehaviorService` busca padrões na `behavior_patterns` que casam com a mensagem atual.
3. **IA:** Constrói um prompt rico contendo: Identidade, Memórias Recentes e Padrões Aplicáveis.
4. **Resposta:** A IA gera a resposta, que pode ser modificada por um template fixo do padrão se a confiança for muito alta.
5. **Estratégia Espelhada:** Se o usuário enviar áudio, o sistema prioriza responder com áudio.

### Ciclo de Aprendizado (Assíncrono)
1. Ao encerrar uma conversa, o `AsyncProcessor` extrai o conteúdo completo.
2. O `LearningService` identifica comportamentos recorrentes.
3. Se um padrão aparece com frequência, um `learning_log` é criado.
4. Se o `confidence_score` for > 0.7, o `SupervisorService` aprova e o padrão vira uma regra ativa em `behavior_patterns`.

## 4. Recomendações para Replicação Multi-Tenant

> [!IMPORTANT]
> Para o projeto Agente Multi-Tenant, as seguintes adaptações são obrigatórias:

1. **Isolamento de Dados:** Adicionar `tenant_id` (ou `affiliate_id`) em todas as tabelas e filtrar todas as consultas RPC.
2. **Escalabilidade de Embeddings:** Avaliar se a geração de embeddings continuará local (SentenceTransformers) ou via API (OpenAI/Cohere) para lidar com múltiplos tenants simultâneos.
3. **Identidade por Tenant:** Cada tenant deve poder configurar seus próprios `behavior_patterns` iniciais (conhecimento específico de negócio).
4. **Isolamento de Vetores:** Garantir que a busca vetorial nunca retorne memórias de outro tenant.

---
**Status da Análise:** 100% Concluída.
**Próximo Passo:** Aguardando autorização para iniciar o planejamento da implementação (Fase 2).
