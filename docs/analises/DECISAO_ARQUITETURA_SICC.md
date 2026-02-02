# Decisão Arquitetural: Reconstrução vs. Refatoração do SICC

Após analisar o código original do SICC no projeto `slim-quality` e compará-lo com as necessidades do novo `agente-multi-tenant`, apresento a recomendação técnica de **Build from Scratch (Criar do Zero)**.

## 1. Por que NÃO refatorar o SICC antigo?

Embora o SICC atual seja robusto, ele sofre de **Acoplamento Profundo (Tight Coupling)** com o monólito anterior:

*   **Dependência de Estrutura Interna:** O código faz uso extensivo de `from ..supabase_client import get_supabase_client` e outros caminhos relativos que não existem no novo backend.
*   **Lógica Single-Tenant Fixa:** O código assume que existe apenas um contexto de banco de dados e uma configuração global de IA. Injetar `tenant_id` em todos os métodos do `LearningService` e `BehaviorService` exigiria mexer em centenas de linhas de lógica de consulta.
*   **Complexidade de Manutenção:** Arquivos como `learning_service.py` possuem mais de 1.100 linhas misturando lógica de negócio com lógica de acesso a dados.
*   **Débito Técnico de Importação:** Existem blocos complexos de `sys.path.append` nos arquivos core do SICC para resolver caminhos, o que é uma prática que queremos evitar no novo sistema limpo.

## 2. Vantagens de Criar o Novo SICC (SICC 2.0)

Ao criar o novo SICC no `agente-multi-tenant`, garantimos:

*   **Multi-Tenancy Nativo:** Toda a estrutura de dados (SQL e Python) será desenhada com `tenant_id` desde o primeiro byte.
*   **Modularidade Real (Interfaces):** Podemos seguir o padrão de "Ports and Adapters". O SICC será um módulo que recebe um `DBProvider` e um `LLMProvider`. Isso facilita a replicação futura para *qualquer* outro projeto.
*   **Integração Nativa com LangGraph:** O SICC antigo era um "serviço lateral". O SICC 2.0 será integrado como **nós oficiais do grafo do LangGraph**, tornando o fluxo de aprendizado muito mais elegante e rastreável.
*   **Modernização:** Uso de Pydantic V2 para validação de dados e `langchain-core` atualizado, eliminando bibliotecas obsoletas.

## 3. Plano de Ação Recomendado (Fase 2)

Utilizaremos o SICC do Slim Quality apenas como **Especificação de Negócio (Reference Map)**.

1.  **Mapear Lógica:** Copiar as "regras de negócio" (ex: como calcular o score de confiança, como extrair padrões de texto) para a nova implementação.
2.  **Schema Multi-Tenant:** Criar as novas tabelas Supabase no `agente-multi-tenant` já preparadas para múltiplos clientes.
3.  **Implementação Modular:** Criar o pacote `app.ai.sicc` no novo projeto de forma totalmente desacoplada.

---
**Conclusão:** Copiar a pasta física e refatorar traria mais "lixo" e complexidade do que construir uma versão moderna e puramente modular aproveitando o conhecimento acumulado.

**Status:** Decisão por "Green Field" documentada.
**Próximo Passo:** Desenho técnico das novas tabelas Multi-Tenant.
