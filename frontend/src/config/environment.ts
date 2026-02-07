/**
 * Configuração e validação de ambiente para o frontend.
 * 
 * Este módulo:
 * - Valida variáveis de ambiente obrigatórias
 * - Detecta ambiente automaticamente
 * - Fornece configuração tipada
 * - Valida URLs de produção vs desenvolvimento
 */

interface EnvironmentConfig {
  apiUrl: string;
  supabaseUrl: string;
  supabaseAnonKey: string;
  environment: 'development' | 'production';
  isDevelopment: boolean;
  isProduction: boolean;
}

class EnvironmentValidator {
  private errors: string[] = [];
  private warnings: string[] = [];

  validate(): { isValid: boolean; errors: string[]; warnings: string[] } {
    this.errors = [];
    this.warnings = [];

    this.validateRequired();
    this.validateUrls();
    this.validateSupabaseConfig();
    this.validateEnvironmentConsistency();

    const isValid = this.errors.length === 0;

    if (!isValid) {
      console.error('❌ Configuração de ambiente inválida:', this.errors);
    }

    if (this.warnings.length > 0) {
      console.warn('⚠️ Avisos de configuração:', this.warnings);
    }

    return {
      isValid,
      errors: [...this.errors],
      warnings: [...this.warnings]
    };
  }

  private validateRequired() {
    const required = {
      'VITE_API_URL': import.meta.env.VITE_API_URL,
      'VITE_SUPABASE_URL': import.meta.env.VITE_SUPABASE_URL,
      'VITE_SUPABASE_ANON_KEY': import.meta.env.VITE_SUPABASE_ANON_KEY,
    };

    for (const [key, value] of Object.entries(required)) {
      if (!value || value.trim() === '') {
        this.errors.push(`Variável de ambiente obrigatória não definida: ${key}`);
      }
    }
  }

  private validateUrls() {
    const apiUrl = import.meta.env.VITE_API_URL;
    const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;

    // Validar formato de URL
    if (apiUrl && !this.isValidUrl(apiUrl)) {
      this.errors.push(`VITE_API_URL inválida: ${apiUrl}`);
    }

    if (supabaseUrl && !this.isValidUrl(supabaseUrl)) {
      this.errors.push(`VITE_SUPABASE_URL inválida: ${supabaseUrl}`);
    }

    // Validar URLs de produção
    const environment = this.getEnvironment();
    
    if (environment === 'production') {
      if (apiUrl && this.isLocalhostUrl(apiUrl)) {
        this.errors.push('VITE_API_URL não pode ser localhost em produção');
      }

      if (supabaseUrl && this.isLocalhostUrl(supabaseUrl)) {
        this.errors.push('VITE_SUPABASE_URL não pode ser localhost em produção');
      }

      // Verificar se é a URL correta do Supabase unificado
      if (supabaseUrl && !supabaseUrl.includes('vtynmmtuvxreiwcxxlma')) {
        this.errors.push('VITE_SUPABASE_URL deve usar o banco unificado (vtynmmtuvxreiwcxxlma)');
      }
    }
  }

  private validateSupabaseConfig() {
    const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY;
    
    if (supabaseKey) {
      // Validar formato JWT
      if (!supabaseKey.startsWith('eyJ')) {
        this.warnings.push('VITE_SUPABASE_ANON_KEY não parece ser um JWT válido');
      }

      // Verificar se não é uma chave de exemplo
      if (supabaseKey.includes('your-anon-key') || supabaseKey === 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9') {
        this.errors.push('VITE_SUPABASE_ANON_KEY não pode ser um valor de exemplo');
      }
    }
  }

  private validateEnvironmentConsistency() {
    const environment = this.getEnvironment();
    const apiUrl = import.meta.env.VITE_API_URL;
    
    // Verificar consistência entre ambiente e URLs
    if (environment === 'development' && apiUrl && !this.isLocalhostUrl(apiUrl)) {
      this.warnings.push('Ambiente development mas API URL não é localhost');
    }

    if (environment === 'production' && apiUrl && this.isLocalhostUrl(apiUrl)) {
      this.warnings.push('Ambiente production mas API URL é localhost');
    }
  }

  private isValidUrl(url: string): boolean {
    try {
      new URL(url);
      return true;
    } catch {
      return false;
    }
  }

  private isLocalhostUrl(url: string): boolean {
    try {
      const parsed = new URL(url);
      return ['localhost', '127.0.0.1', '0.0.0.0'].includes(parsed.hostname);
    } catch {
      return false;
    }
  }

  private getEnvironment(): 'development' | 'production' {
    const envVar = import.meta.env.VITE_ENVIRONMENT;
    
    if (envVar === 'production') return 'production';
    if (envVar === 'development') return 'development';
    
    // Auto-detectar baseado na URL da API
    const apiUrl = import.meta.env.VITE_API_URL;
    if (apiUrl && this.isLocalhostUrl(apiUrl)) {
      return 'development';
    }
    
    // Default para production se não conseguir detectar
    return 'production';
  }
}

// Validar configuração na inicialização
const validator = new EnvironmentValidator();
const validation = validator.validate();

if (!validation.isValid) {
  throw new Error(`Configuração de ambiente inválida: ${validation.errors.join(', ')}`);
}

// Detectar ambiente
const environment = import.meta.env.VITE_ENVIRONMENT === 'production' ? 'production' : 'development';

// Configuração exportada
export const config: EnvironmentConfig = {
  apiUrl: import.meta.env.VITE_API_URL,
  supabaseUrl: import.meta.env.VITE_SUPABASE_URL,
  supabaseAnonKey: import.meta.env.VITE_SUPABASE_ANON_KEY,
  environment,
  isDevelopment: environment === 'development',
  isProduction: environment === 'production',
};

// Log da configuração (sem expor secrets)
console.log('🔧 Configuração do ambiente:', {
  environment: config.environment,
  apiUrl: config.apiUrl,
  supabaseUrl: config.supabaseUrl,
  hasSupabaseKey: !!config.supabaseAnonKey,
  isDevelopment: config.isDevelopment,
  isProduction: config.isProduction,
});

// Avisos específicos
if (validation.warnings.length > 0) {
  console.warn('⚠️ Avisos de configuração:', validation.warnings);
}

if (config.isDevelopment) {
  console.log('🚧 Executando em modo desenvolvimento');
} else {
  console.log('🚀 Executando em modo produção');
}

export default config;