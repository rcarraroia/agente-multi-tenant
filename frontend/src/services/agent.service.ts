/**
 * Serviço de API para operações do Agente IA.
 * 
 * Gerencia todas as chamadas relacionadas à ativação,
 * configuração e monitoramento de agentes IA.
 */

import api from './api';
import { supabase } from '../lib/supabase';

export interface AgentActivationRequest {
  agentName: string;
  agentPersonality: string;
  activationReason?: string;
  subscriptionId?: string;
  metadata?: Record<string, any>;
}

export interface AgentActivationResponse {
  id: string;
  affiliateId: string;
  tenantId: string;
  agentName: string;
  agentPersonality: string;
  status: 'active' | 'pending' | 'suspended' | 'expired' | 'failed';
  activatedAt: string;
  subscriptionValid: boolean;
  subscriptionExpiresAt?: string;
  metadata?: Record<string, any>;
}

export interface ActivationStatusResponse {
  affiliateId: string;
  hasActiveAgent: boolean;
  agentName?: string;
  agentPersonality?: string;
  status?: string;
  activatedAt?: string;
  expiresAt?: string;
  tenantId?: string;
  subscriptionValid?: boolean;
  daysUntilExpiration?: number;
  canReactivate: boolean;
  reactivationBlockedReason?: string;
}

export interface ApiError {
  message: string;
  details?: string;
  code?: string;
}

class AgentService {
  private async makeRequest<T>(
    endpoint: string,
    options: {
      method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
      data?: any;
    } = {}
  ): Promise<T> {
    try {
      const response = await api.request({
        url: endpoint,
        method: options.method || 'GET',
        data: options.data,
      });
      
      return response.data;
    } catch (error: any) {
      // Tratar erros do axios
      if (error.response) {
        // Erro HTTP com resposta do servidor
        const errorData = error.response.data;
        throw new Error(
          errorData.message || 
          errorData.detail || 
          `HTTP ${error.response.status}: ${error.response.statusText}`
        );
      } else if (error.request) {
        // Erro de rede
        throw new Error('Erro de rede ou servidor indisponível');
      } else {
        // Outro tipo de erro
        throw new Error(error.message || 'Erro desconhecido');
      }
    }
  }

  private async getAuthToken(): Promise<string | null> {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      return session?.access_token || null;
    } catch (error) {
      console.error('Erro ao obter token:', error);
      return null;
    }
  }

  /**
   * Ativa um agente IA para o afiliado atual.
   */
  async activateAgent(data: AgentActivationRequest): Promise<AgentActivationResponse> {
    return this.makeRequest<AgentActivationResponse>('/agent/activate', {
      method: 'POST',
      data,
    });
  }

  /**
   * Desativa o agente IA do afiliado atual.
   */
  async deactivateAgent(reason: string = 'Desativado pelo usuário'): Promise<void> {
    return this.makeRequest<void>('/agent/deactivate', {
      method: 'POST',
      data: { reason },
    });
  }

  /**
   * Obtém o status de ativação do agente para o afiliado atual.
   */
  async getActivationStatus(): Promise<ActivationStatusResponse> {
    return this.makeRequest<ActivationStatusResponse>('/agent/status');
  }

  /**
   * Valida e atualiza o status de ativação.
   */
  async validateActivation(): Promise<{
    isValid: boolean;
    status: string;
    validationErrors?: string[];
    validationWarnings?: string[];
  }> {
    return this.makeRequest('/agent/validate');
  }

  /**
   * Obtém configurações do agente.
   */
  async getAgentConfig(): Promise<{
    agentName: string;
    agentPersonality: string;
    settings: Record<string, any>;
  }> {
    return this.makeRequest('/agent/config');
  }

  /**
   * Atualiza configurações do agente.
   */
  async updateAgentConfig(config: {
    agentName?: string;
    agentPersonality?: string;
    settings?: Record<string, any>;
  }): Promise<void> {
    return this.makeRequest('/agent/config', {
      method: 'PUT',
      data: config,
    });
  }

  /**
   * Obtém métricas do agente (conversas, performance, etc.).
   */
  async getAgentMetrics(period: '24h' | '7d' | '30d' = '7d'): Promise<{
    totalConversations: number;
    activeConversations: number;
    averageResponseTime: number;
    satisfactionScore: number;
    topQuestions: Array<{ question: string; count: number }>;
    conversationsByDay: Array<{ date: string; count: number }>;
  }> {
    return this.makeRequest(`/agent/metrics?period=${period}`);
  }

  /**
   * Obtém histórico de conversas do agente.
   */
  async getConversationHistory(
    page: number = 1,
    limit: number = 20,
    filters?: {
      startDate?: string;
      endDate?: string;
      status?: string;
    }
  ): Promise<{
    conversations: Array<{
      id: string;
      customerName?: string;
      customerPhone?: string;
      startedAt: string;
      endedAt?: string;
      status: string;
      messageCount: number;
      lastMessage: string;
    }>;
    total: number;
    page: number;
    totalPages: number;
  }> {
    const params = new URLSearchParams({
      page: page.toString(),
      limit: limit.toString(),
      ...filters,
    });

    return this.makeRequest(`/agent/conversations?${params}`);
  }

  /**
   * Testa conectividade com a API.
   */
  async testConnection(): Promise<{
    status: 'ok' | 'error';
    message: string;
    timestamp: string;
  }> {
    try {
      return await this.makeRequest('/health');
    } catch (error) {
      return {
        status: 'error',
        message: error instanceof Error ? error.message : 'Erro desconhecido',
        timestamp: new Date().toISOString(),
      };
    }
  }
}

// Instância singleton do serviço
export const agentService = new AgentService();

// Utilitários para tratamento de erros
export const handleApiError = (error: unknown): string => {
  if (error instanceof Error) {
    return error.message;
  }
  
  if (typeof error === 'string') {
    return error;
  }
  
  return 'Erro desconhecido na API';
};

export const isNetworkError = (error: unknown): boolean => {
  if (error instanceof Error) {
    return error.message.includes('fetch') || 
           error.message.includes('network') ||
           error.message.includes('servidor indisponível');
  }
  return false;
};

export default agentService;