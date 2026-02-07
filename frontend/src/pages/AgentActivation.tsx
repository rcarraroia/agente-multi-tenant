/**
 * Página de Ativação de Agente IA.
 * 
 * Permite que afiliados ativem seus agentes IA personalizados
 * com validação de assinatura e feedback completo.
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bot, User, MessageSquare, Settings, CheckCircle, AlertCircle } from 'lucide-react';
import { useToast, useAsyncOperation } from '../components/ui/toast';
import { ButtonLoading, LoadingMessage, CardSkeleton } from '../components/ui/loading';
import { agentService } from '../services/agent.service';

interface AgentActivationForm {
  agentName: string;
  agentPersonality: string;
  activationReason?: string;
  metadata?: Record<string, any>;
}

interface ActivationStatus {
  hasActiveAgent: boolean;
  agentName?: string;
  agentPersonality?: string;
  status?: string;
  activatedAt?: string;
  expiresAt?: string;
  canReactivate?: boolean;
  reactivationBlockedReason?: string;
}

const AgentActivation: React.FC = () => {
  const navigate = useNavigate();
  const { showSuccess, showError, showWarning } = useToast();
  const { execute: executeAsync, loading: asyncLoading } = useAsyncOperation();
  
  const [form, setForm] = useState<AgentActivationForm>({
    agentName: '',
    agentPersonality: 'assistente',
    activationReason: '',
    metadata: {}
  });
  
  const [status, setStatus] = useState<ActivationStatus | null>(null);
  const [loadingStatus, setLoadingStatus] = useState(true);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);

  // Carregar status atual na inicialização
  useEffect(() => {
    loadActivationStatus();
  }, []);

  const loadActivationStatus = async () => {
    try {
      setLoadingStatus(true);
      const response = await agentService.getActivationStatus();
      setStatus(response);
      
      // Pre-preencher formulário se já houver agente
      if (response.hasActiveAgent && response.agentName) {
        setForm(prev => ({
          ...prev,
          agentName: response.agentName || '',
          agentPersonality: response.agentPersonality || 'assistente'
        }));
      }
    } catch (error) {
      showError(
        'Erro ao carregar status',
        'Não foi possível verificar o status da ativação'
      );
    } finally {
      setLoadingStatus(false);
    }
  };

  const validateForm = (): boolean => {
    const errors: string[] = [];

    if (!form.agentName.trim()) {
      errors.push('Nome do agente é obrigatório');
    } else if (form.agentName.length < 3) {
      errors.push('Nome do agente deve ter pelo menos 3 caracteres');
    } else if (form.agentName.length > 50) {
      errors.push('Nome do agente deve ter no máximo 50 caracteres');
    }

    if (!form.agentPersonality) {
      errors.push('Personalidade do agente é obrigatória');
    }

    setValidationErrors(errors);
    return errors.length === 0;
  };

  const handleActivation = async () => {
    if (!validateForm()) {
      showError('Formulário inválido', 'Corrija os erros antes de continuar');
      return;
    }

    const result = await executeAsync(
      () => agentService.activateAgent(form),
      {
        loadingMessage: 'Ativando seu agente IA...',
        successMessage: 'Agente ativado com sucesso!',
        errorMessage: 'Falha na ativação do agente',
        onSuccess: () => {
          // Recarregar status após ativação
          loadActivationStatus();
        }
      }
    );

    if (result) {
      // Redirecionar para dashboard após sucesso
      setTimeout(() => {
        navigate('/dashboard');
      }, 2000);
    }
  };

  const handleDeactivation = async () => {
    if (!confirm('Tem certeza que deseja desativar seu agente? Esta ação pode ser revertida.')) {
      return;
    }

    const result = await executeAsync(
      () => agentService.deactivateAgent('Desativado pelo usuário'),
      {
        loadingMessage: 'Desativando agente...',
        successMessage: 'Agente desativado com sucesso',
        errorMessage: 'Falha na desativação do agente',
        onSuccess: () => {
          loadActivationStatus();
        }
      }
    );
  };

  const getPersonalityDescription = (personality: string): string => {
    const descriptions = {
      assistente: 'Profissional e prestativo, focado em resolver problemas',
      amigavel: 'Caloroso e acolhedor, cria conexões pessoais',
      tecnico: 'Preciso e detalhado, especialista em soluções técnicas',
      consultivo: 'Analítico e estratégico, oferece insights valiosos',
      casual: 'Descontraído e acessível, conversa naturalmente'
    };
    return descriptions[personality as keyof typeof descriptions] || 'Personalidade personalizada';
  };

  if (loadingStatus) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="mb-8">
          <CardSkeleton lines={2} />
        </div>
        <CardSkeleton lines={4} />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center space-x-3 mb-4">
          <Bot className="w-8 h-8 text-blue-600" />
          <h1 className="text-3xl font-bold text-gray-900">
            Ativação do Agente IA
          </h1>
        </div>
        <p className="text-gray-600">
          Configure e ative seu agente IA personalizado para atendimento automatizado.
        </p>
      </div>

      {/* Status Atual */}
      {status && (
        <div className="mb-8">
          <div className={`
            border rounded-lg p-6
            ${status.hasActiveAgent 
              ? 'bg-green-50 border-green-200' 
              : 'bg-yellow-50 border-yellow-200'
            }
          `}>
            <div className="flex items-start space-x-3">
              {status.hasActiveAgent ? (
                <CheckCircle className="w-6 h-6 text-green-600 mt-0.5" />
              ) : (
                <AlertCircle className="w-6 h-6 text-yellow-600 mt-0.5" />
              )}
              <div className="flex-1">
                <h3 className="font-semibold text-gray-900 mb-2">
                  {status.hasActiveAgent ? 'Agente Ativo' : 'Agente Inativo'}
                </h3>
                
                {status.hasActiveAgent ? (
                  <div className="space-y-2 text-sm text-gray-700">
                    <p><strong>Nome:</strong> {status.agentName}</p>
                    <p><strong>Personalidade:</strong> {getPersonalityDescription(status.agentPersonality || '')}</p>
                    {status.activatedAt && (
                      <p><strong>Ativado em:</strong> {new Date(status.activatedAt).toLocaleDateString('pt-BR')}</p>
                    )}
                    {status.expiresAt && (
                      <p><strong>Expira em:</strong> {new Date(status.expiresAt).toLocaleDateString('pt-BR')}</p>
                    )}
                  </div>
                ) : (
                  <div className="space-y-2 text-sm text-gray-700">
                    <p>Seu agente IA não está ativo no momento.</p>
                    {status.reactivationBlockedReason && (
                      <p className="text-red-600">
                        <strong>Motivo:</strong> {status.reactivationBlockedReason}
                      </p>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Formulário de Ativação */}
      <div className="bg-white border rounded-lg p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-6 flex items-center">
          <Settings className="w-5 h-5 mr-2" />
          Configuração do Agente
        </h2>

        <div className="space-y-6">
          {/* Nome do Agente */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Nome do Agente *
            </label>
            <div className="relative">
              <User className="absolute left-3 top-3 w-4 h-4 text-gray-400" />
              <input
                type="text"
                value={form.agentName}
                onChange={(e) => setForm(prev => ({ ...prev, agentName: e.target.value }))}
                placeholder="Ex: Assistente Virtual, BIA, Atendente..."
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                maxLength={50}
              />
            </div>
            <p className="text-xs text-gray-500 mt-1">
              Este será o nome que seus clientes verão nas conversas
            </p>
          </div>

          {/* Personalidade */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Personalidade do Agente *
            </label>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {[
                { value: 'assistente', label: 'Assistente Profissional', desc: 'Formal e prestativo' },
                { value: 'amigavel', label: 'Amigável', desc: 'Caloroso e acolhedor' },
                { value: 'tecnico', label: 'Técnico Especialista', desc: 'Preciso e detalhado' },
                { value: 'consultivo', label: 'Consultor Estratégico', desc: 'Analítico e insights' },
                { value: 'casual', label: 'Casual', desc: 'Descontraído e natural' }
              ].map((personality) => (
                <label
                  key={personality.value}
                  className={`
                    relative flex items-start p-3 border rounded-lg cursor-pointer
                    ${form.agentPersonality === personality.value
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300'
                    }
                  `}
                >
                  <input
                    type="radio"
                    name="personality"
                    value={personality.value}
                    checked={form.agentPersonality === personality.value}
                    onChange={(e) => setForm(prev => ({ ...prev, agentPersonality: e.target.value }))}
                    className="sr-only"
                  />
                  <div className="flex-1">
                    <div className="font-medium text-gray-900">{personality.label}</div>
                    <div className="text-sm text-gray-600">{personality.desc}</div>
                  </div>
                  {form.agentPersonality === personality.value && (
                    <CheckCircle className="w-5 h-5 text-blue-600" />
                  )}
                </label>
              ))}
            </div>
          </div>

          {/* Motivo da Ativação */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Motivo da Ativação (Opcional)
            </label>
            <div className="relative">
              <MessageSquare className="absolute left-3 top-3 w-4 h-4 text-gray-400" />
              <textarea
                value={form.activationReason}
                onChange={(e) => setForm(prev => ({ ...prev, activationReason: e.target.value }))}
                placeholder="Descreva brevemente o motivo da ativação..."
                rows={3}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                maxLength={200}
              />
            </div>
          </div>

          {/* Erros de Validação */}
          {validationErrors.length > 0 && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <div className="flex items-start space-x-2">
                <AlertCircle className="w-5 h-5 text-red-600 mt-0.5" />
                <div>
                  <h4 className="font-medium text-red-800">Corrija os seguintes erros:</h4>
                  <ul className="mt-2 text-sm text-red-700 list-disc list-inside">
                    {validationErrors.map((error, index) => (
                      <li key={index}>{error}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          )}

          {/* Botões de Ação */}
          <div className="flex flex-col sm:flex-row gap-4 pt-6 border-t">
            {status?.hasActiveAgent ? (
              <>
                <ButtonLoading
                  loading={asyncLoading}
                  onClick={handleActivation}
                  className="bg-blue-600 hover:bg-blue-700"
                >
                  Atualizar Configurações
                </ButtonLoading>
                <ButtonLoading
                  loading={asyncLoading}
                  onClick={handleDeactivation}
                  className="bg-red-600 hover:bg-red-700"
                >
                  Desativar Agente
                </ButtonLoading>
              </>
            ) : (
              <ButtonLoading
                loading={asyncLoading}
                onClick={handleActivation}
                disabled={!status?.canReactivate}
                className="bg-green-600 hover:bg-green-700 disabled:bg-gray-400"
              >
                {status?.canReactivate ? 'Ativar Agente' : 'Ativação Bloqueada'}
              </ButtonLoading>
            )}
            
            <button
              onClick={() => navigate('/dashboard')}
              className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Voltar ao Dashboard
            </button>
          </div>
        </div>
      </div>

      {/* Informações Adicionais */}
      <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-6">
        <h3 className="font-semibold text-blue-900 mb-3">ℹ️ Informações Importantes</h3>
        <ul className="text-sm text-blue-800 space-y-2">
          <li>• Seu agente será ativado imediatamente após a confirmação</li>
          <li>• A ativação requer uma assinatura válida do serviço</li>
          <li>• Você pode alterar as configurações a qualquer momento</li>
          <li>• O agente funcionará 24/7 para atender seus clientes</li>
          <li>• Todas as conversas são registradas para análise e melhoria</li>
        </ul>
      </div>
    </div>
  );
};

export default AgentActivation;