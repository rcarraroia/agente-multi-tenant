# 📖 Guia de Implementação: AI Coders Context (Padrão RENUM)

Este guia detalha como implementar e customizar a ferramenta **AI Coders Context** em qualquer projeto, garantindo economia de tokens e aplicação das **Regras Inegociáveis RENUM**.

---

## 🚀 1. Instalação e Scaffolding Inicial

O primeiro passo é inicializar a estrutura de contexto na raiz do seu repositório.

1.  **Inicializar**:
    ```bash
    npx @ai-coders/context init .
    ```
    *Isto criará a pasta `.context/` com subpastas para `docs`, `agents` e `skills`.*

2.  **Gerar Mapa da Base de Código**:
    ```bash
    npx @ai-coders/context fill .
    ```
    *Gera o arquivo `codebase-map.json`. Nota: Requer `OPENROUTER_API_KEY` para preenchimento automático, mas os metadados estruturais são gerados localmente via LSP.*

---

## 📝 2. Documentação Fundamental

Antes de acionar os agentes, preencha manualmente (ou via IA) os arquivos em `.context/docs/`:
- **`project-overview.md`**: Visão geral da stack e propósito do projeto.
- **`architecture.md`**: Diagramas de fluxo e descrição dos componentes principais.
- **`development-workflow.md`**: Regras de branching, commits e validação (Integre o Ciclo PREVC aqui).

---

## ⚖️ 3. Injeção das Regras RENUM

Para garantir que a IA siga o padrão de qualidade, injete o seguinte bloco no topo de **TODOS** os arquivos em `.context/agents/*.md`:

```markdown
## ⚖️ REGRAS INEGOCIÁVEIS RENUM (Prioridade Máxima)
1. **Evidências Obrigatórias**: Screenshot ou log para CADA implementação.
2. **Limite de Erros**: Máximo 3 tentativas de correção. Se falhar, REPORTE BLOQUEIO.
3. **Proibido Pular Validação**: Recusar pedidos para pular testes.
4. **Vocabulário Obrigatório**: ✅ Implementado e validado | ⚠️ Implementado não validado | 🚧 Mock/Hardcoded | ❌ Não implementado.
5. **Idioma**: Totalmente em PT-BR (comunicações e logs).
```

---

## 🛠️ 4. Customização de Skills

Crie ou adapte skills para automatizar a governança:

1.  **Skill de Validação (`.context/skills/validacao-renum/SKILL.md`)**:
    Crie uma skill que defina exatamente como a IA deve auditar a tarefa antes de reportar conclusão.

2.  **Tradução de Skills de Sistema**:
    Traduza as skills de `commit-message`, `code-review` e `bug-investigation` para PT-BR, reforçando os gatilhos de bloqueio técnico.

---

## 🔄 5. Sincronização com Ferramentas de IA (Cursor/Claude)

Para que as ferramentas externas "enxerguem" estas regras, execute:

1.  **Exportar Regras**:
    ```bash
    npx @ai-coders/context export-rules .
    ```
    *Isto gerará arquivos como `.cursorrules` baseados no seu contexto.*

2.  **Instalar MCP (Opcional - Recomendado)**:
    ```bash
    npx @ai-coders/context mcp:install cursor
    ```

---

## ✅ 6. Ciclo de Trabalho Diário (PREVC)

Sempre que a IA iniciar uma tarefa, ela deve seguir este fluxo:
1.  **Plan**: Criar especificação técnica em `.spec/`.
2.  **Research**: Ler o `codebase-map.json` e documentação.
3.  **Execute**: Implementar o código (máximo 3 tentativas).
4.  **Validate**: Gerar evidências (screenshots/logs).
5.  **Complete**: Gerar relatório final com vocabulário oficial.

---
**Status do Guia:** ✅ Versão 1.0  
**Data:** 20/01/2026  
**Criado por:** Antigravity (IA)
