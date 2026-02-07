/**
 * Serviço de API para operações do Agente IA.
 * 
 * Gerencia todas as chamadas relacionadas à ativação,
 * configuração e monitoramento de agentes IA.
 */

import { config } from '../config/environment';

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
  private baseUrl: string;

  constructor() {
    this.baseUrl = config.apiUrl;
  }

  private async makeRequest<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    
    // Obter token JWT do localStorage ou context
    const token = this.getAuthToken();
    
    const defaultHeaders: HeadersInit = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };

    if (token) {
      defaultHeaders['Authorization'] = `Bearer ${token}`;
    }

    const config: RequestInit = {
      ...options,
      headers: {
        ...defaultHeaders,
        ...options.headers,
      },
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          errorData.message || 
          errorData.detail || 
          `HTTP ${response.status}: ${response.statusText}`
        );
      }

      // Handle empty responses
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        return await response.json();
      } else {
        return {} as T;
      }
    } catch (error) {
      if (error instanceof Error) {
        throw error;
      }
      throw new Error('Erro de rede ou servidor indisponível');
    }
  }

  private getAuthToken(): string | null {
    // Em um app real, isso viria do context de autenticação
    // Por enquanto, vamos simular ou usar localStorage
    return localStorage.getItem('auth_token') || null;
  }

  /**
   * Ativa um agente IA para o afiliado atual.
   */
  async activateAgent(data: AgentActivationRequest): Promise<AgentActivationResponse> {
    return this.makeRequest<AgentActivationResponse>('/agent/activate', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  /**
   * Desativa o agente IA do afiliado atual.
   */
  async deactivateAgent(reason: string = 'Desativado pelo usuário'): Promise<void> {
    return this.makeRequest<void>('/agent/deactivate', {
      method: 'POST',
      body: JSON.stringify({ reason }),
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
      body: JSON.stringify(config),
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