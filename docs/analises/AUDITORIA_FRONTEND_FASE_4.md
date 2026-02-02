# Auditoria e Estratégia: Fase 4 - Frontend (Multi-Tenant)

Fizemos uma auditoria detalhada nos painéis existentes do sistema **Slim Quality** (referência) e na estrutura atual do **Agente Multi-Tenant**.

## ⚖️ Situação Atual

1.  **Tecnologia (Slim Quality):** O sistema atual utiliza **React + Vite + Tailwind CSS + Shadcn UI**. Esta é uma escolha excelente por ser moderna, performática e modular.
2.  **Componentes Referência:**
    *   **Afiliados:** O arquivo `Configuracoes.tsx` e `Dashboard.tsx` (Afiliados) já possuem lógica de integração com Supabase e Asaas.
    *   **Agente IA (Admin):** No diretório `dashboard/agente`, encontramos telas completas de configuração (`AgenteConfiguracao.tsx`) e refinamento (`AgenteAprendizados.tsx`).
3.  **Agente Multi-Tenant:** Atualmente possui apenas a pasta `/frontend` vazia, indicando que a implementação será iniciada do zero, permitindo uma arquitetura mais limpa e focada exclusivamente no multi-tenant.

## 🚀 Proposta de Execução (FASE 4)

### 1. Stack Tecnológica
Manteremos a consistência com o ecossistema Slim Quality para facilitar a manutenção e permitir o reuso de componentes de lógica:
- **Framework:** React + Vite (non-SSR para máxima velocidade no painel).
- **Styling:** Tailwind CSS + Shadcn UI + Framer Motion (para o efeito "WOW").
- **State Management:** React Query (TanStack) para cache de mensagens e dados do agente.
- **Icons:** Lucide React (padrão do sistema).

### 2. Divisão de Interfaces: Admin vs Afiliado

> [!IMPORTANT]
> **Recomendação de Escopo:**
> Sugerimos que a **Configuração Geral do Agente** (o que o afiliado mexe) seja feita na **Fase 4**, enquanto o **Dashboard Analítico Global** (o que você, admin, vê de todos) fique para a **Fase 5**.

#### **Portal do Afiliado (Fase 4)**
- **Dashboard Principal:** Status do agente, saldo e métricas rápidas.
- **Meu Agente:** Personalização da "voz", instruções e ativação de Skills (Vendas, Suporte).
- **Central de Chat:** Interface de acompanhamento em tempo real das conversas que a IA está tendo.
- **CRM Kanban:** Gestão visual dos leads capturados.

#### **Painel do Admin (Fase 5)**
- **Gestão de Tenants:** Visualizar todos os afiliados ativos.
- **Oversight de IA:** Monitorar alucinações de todos os agentes e ajustar o "Supervisor Global".
- **Marketplace de Skills:** Ativação/Desativação de funcionalidades por plano.

## 🎨 Design (Diretrizes UI-UX Pro Max)
Para gerar o efeito de "produto premium", aplicaremos:
- **Glassmorphism:** Em cards e barras de navegação.
- **Micro-interações:** Feedback visual em cada clique e mudança de estado da IA.
- **Dark/Light Mode:** Suporte nativo desde o dia 1.

## 📋 Próximos Passos (Aprovação Necessária)
1.  **[ ]** Aprovar inicialização do projeto React na pasta `/frontend`.
2.  **[ ]** Definir se utilizaremos um Subdomínio (ex: `agente.slimquality.com.br`) ou se será integrado ao painel principal.
3.  **[ ]** Decidir se iniciamos agora a interface administrativa de "Oversight" ou se focamos 100% no Afiliado primeiro.

---
**Nenhuma alteração de código foi realizada.** Aguardo sua direção estratégica.
