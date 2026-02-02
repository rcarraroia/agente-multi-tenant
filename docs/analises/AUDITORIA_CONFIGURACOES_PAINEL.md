# Auditoria Profunda: Requisitos de Configuração (Painel do Afiliado - Fase 4)

Realizei uma auditoria técnica em todo o sistema `agente-multi-tenant` para identificar exatamente o que precisaremos construir no Painel do Afiliado e o que ainda falta no Backend para suportar essas configurações.

## 🔍 Mapa de Configurações Necessárias

### 1. Integração WhatsApp (Evolution API) ✅ (Backend Pronto)
*   **Estado Atual:** O sistema já possui os endpoints para criar instâncias, verificar status e recuperar o QR Code em Base64.
*   **O que o Painel precisa:**
    *   Botão "Conectar WhatsApp" (chama `/connect`).
    *   Monitoramento de Status (chama `/status` em loop/polling).
    *   Visualizador de QR Code (renderiza o Base64 retornado por `/qrcode`).
    *   Botão "Desconectar" (para limpar a instância).

### 2. Credenciais de IA (OpenAI API Key) ⚠️ (Pendente no Backend)
*   **Estado Atual:** O sistema utiliza uma chave global (`OPENAI_API_KEY`) definida no `.env`. Não há campo na tabela do tenant para chaves individuais.
*   **Gap Identificado:** Conforme você solicitou, cada afiliado deve usar sua própria chave.
*   **Ação Necessária:**
    *   Adicionar campo `openai_api_key` na tabela `multi_agent_tenants`.
    *   Modificar a inicialização do LLM para carregar a chave do tenant em tempo de execução.

### 3. Personalidade do Agente ✅ (Backend Pronto)
*   **Estado Atual:** Já temos os campos `agent_name` e `agent_personality` no banco e no esquema.
*   **O que o Painel precisa:**
    *   Campo de texto para o nome (Ex: "BIA").
    *   Área de texto para a "Instrução Base" (Ex: "Você é um vendedor focado em...").

### 4. Google Calendar e Meet ❌ (Totalmente Pendente)
*   **Estado Atual:** **Não existe código** referente ao Google no backend atual.
*   **Impacto:** Esta é uma funcionalidade complexa que exige:
    *   Fluxo de OAuth 2.0 (Botão "Conectar com Google").
    *   Armazenamento de Refresh Tokens por tenant.
    *   Novas "Skills" para o agente conseguir ler agenda e gerar links de Meet.
*   **Recomendação:** Se for essencial para a Fase 4, precisaremos criar uma especificação técnica exclusiva para esta integração (FASE 4.1).

### 5. Gestão de Funil CRM ✅ (Backend Pronto)
*   **Estado Atual:** O sistema já cria automaticamente um funil de 6 etapas para cada novo tenant.
*   **O que o Painel precisa:**
    *   Visualização tipo Kanban dos cards/leads.
    *   Possibilidade de renomear etapas ou mudar cores.

---

## 📋 Conclusão da Auditoria
O backend está robusto em WhatsApp e CRM, mas precisa de atualizações de schema para **API Keys individuais** e uma nova implementação do zero para **Google Calendar/Meet**.

**Deseja que eu prepare a especificação para a integração com Google antes de começarmos o Frontend, ou deixamos o Google para uma fase posterior e focamos no que já está pronto?**
