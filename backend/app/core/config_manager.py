"""
Configuration Manager para validação e gestão de configurações de produção.

Este módulo implementa validações rigorosas para garantir que o sistema
esteja configurado adequadamente para ambiente de produção, incluindo:
- Validação de variáveis de ambiente obrigatórias
- Verificação de URLs de produção vs localhost
- Validação de JWT secrets seguros
- Verificação de conectividade com serviços externos
"""

import os
import re
import secrets
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import urlparse
from app.config import settings
from app.core.logging import get_logger
from app.core.exceptions import EntityNotFoundException

logger = get_logger(__name__)

class ConfigurationError(Exception):
    """Exceção para erros de configuração críticos."""
    pass

class ConfigurationManager:
    """
    Gerenciador de configuração com validações para produção.
    
    Responsabilidades:
    - Validar variáveis de ambiente obrigatórias
    - Verificar segurança de secrets
    - Validar URLs de produção
    - Verificar conectividade com serviços externos
    """
    
    def __init__(self):
        self.environment = settings.ENVIRONMENT.lower()
        self.is_production = self.environment == "production"
        self.is_development = self.environment == "development"
        self.validation_errors: List[str] = []
        self.validation_warnings: List[str] = []
        
    def validate_all(self, strict: bool = True) -> Tuple[bool, List[str], List[str]]:
        """
        Executa todas as validações de configuração.
        
        Args:
            strict: Se True, falha em qualquer erro. Se False, apenas coleta erros.
            
        Returns:
            Tuple[is_valid, errors, warnings]
        """
        logger.info(f"🔍 Iniciando validação de configuração para ambiente: {self.environment}")
        
        self.validation_errors.clear()
        self.validation_warnings.clear()
        
        # Executar todas as validações
        self._validate_required_environment_variables()
        self._validate_database_configuration()
        self._validate_security_configuration()
        self._validate_external_services_configuration()
        self._validate_cors_configuration()
        
        if self.is_production:
            self._validate_production_specific_settings()
            
        # Log dos resultados
        if self.validation_errors:
            logger.error(f"❌ Validação falhou com {len(self.validation_errors)} erros:")
            for error in self.validation_errors:
                logger.error(f"  - {error}")
                
        if self.validation_warnings:
            logger.warning(f"⚠️ Encontrados {len(self.validation_warnings)} avisos:")
            for warning in self.validation_warnings:
                logger.warning(f"  - {warning}")
                
        is_valid = len(self.validation_errors) == 0
        
        if is_valid:
            logger.info("✅ Validação de configuração concluída com sucesso")
        else:
            logger.error("❌ Validação de configuração falhou")
            
        if strict and not is_valid:
            raise ConfigurationError(
                f"Configuração inválida: {len(self.validation_errors)} erros encontrados"
            )
            
        return is_valid, self.validation_errors.copy(), self.validation_warnings.copy()
    
    def _validate_required_environment_variables(self):
        """Valida se todas as variáveis de ambiente obrigatórias estão definidas."""
        logger.debug("🔍 Validando variáveis de ambiente obrigatórias")
        
        required_vars = {
            'SUPABASE_URL': settings.SUPABASE_URL,
            'SUPABASE_SERVICE_KEY': settings.SUPABASE_SERVICE_KEY,
            'JWT_SECRET_KEY': settings.JWT_SECRET_KEY,
        }
        
        # Variáveis obrigatórias apenas em produção
        if self.is_production:
            production_required = {
                'SUPABASE_JWT_SECRET': settings.SUPABASE_JWT_SECRET,
                'OPENAI_API_KEY': settings.OPENAI_API_KEY,
                'EVOLUTION_API_URL': settings.EVOLUTION_API_URL,
                'EVOLUTION_API_KEY': settings.EVOLUTION_API_KEY,
                'CHATWOOT_URL': settings.CHATWOOT_URL,
                'CHATWOOT_ADMIN_TOKEN': settings.CHATWOOT_ADMIN_TOKEN,
            }
            required_vars.update(production_required)
        
        for var_name, var_value in required_vars.items():
            if not var_value or (isinstance(var_value, str) and var_value.strip() == ""):
                self.validation_errors.append(
                    f"Variável de ambiente obrigatória não definida: {var_name}"
                )
            else:
                logger.debug(f"✅ {var_name}: definida")
    
    def _validate_database_configuration(self):
        """Valida configuração do banco de dados Supabase."""
        logger.debug("🔍 Validando configuração do banco de dados")
        
        # Validar URL do Supabase
        if settings.SUPABASE_URL:
            if not self._is_valid_url(settings.SUPABASE_URL):
                self.validation_errors.append(
                    f"SUPABASE_URL inválida: {settings.SUPABASE_URL}"
                )
            elif self.is_production and self._is_localhost_url(settings.SUPABASE_URL):
                self.validation_errors.append(
                    "SUPABASE_URL não pode ser localhost em produção"
                )
            else:
                logger.debug(f"✅ SUPABASE_URL válida: {settings.SUPABASE_URL}")
        
        # Validar chaves do Supabase
        if settings.SUPABASE_SERVICE_KEY:
            if not settings.SUPABASE_SERVICE_KEY.startswith('eyJ'):
                self.validation_warnings.append(
                    "SUPABASE_SERVICE_KEY não parece ser um JWT válido"
                )
            else:
                logger.debug("✅ SUPABASE_SERVICE_KEY tem formato JWT válido")
    
    def _validate_security_configuration(self):
        """Valida configurações de segurança."""
        logger.debug("🔍 Validando configurações de segurança")
        
        # Validar JWT_SECRET_KEY
        if settings.JWT_SECRET_KEY:
            if len(settings.JWT_SECRET_KEY) < 32:
                self.validation_errors.append(
                    "JWT_SECRET_KEY deve ter pelo menos 32 caracteres"
                )
            elif settings.JWT_SECRET_KEY in ['your-secret-key', 'secret', 'password', '123456']:
                self.validation_errors.append(
                    "JWT_SECRET_KEY não pode ser um valor padrão inseguro"
                )
            elif self.is_production and not self._is_secure_secret(settings.JWT_SECRET_KEY):
                self.validation_warnings.append(
                    "JWT_SECRET_KEY pode não ser suficientemente seguro para produção"
                )
            else:
                logger.debug("✅ JWT_SECRET tem comprimento adequado")
        
        # Validar algoritmo JWT
        if settings.JWT_ALGORITHM not in ['HS256', 'HS384', 'HS512', 'RS256']:
            self.validation_warnings.append(
                f"Algoritmo JWT não recomendado: {settings.JWT_ALGORITHM}"
            )
        else:
            logger.debug(f"✅ Algoritmo JWT válido: {settings.JWT_ALGORITHM}")
        
        # Validar tempo de expiração do token
        if settings.ACCESS_TOKEN_EXPIRE_MINUTES > 60 * 24 * 30:  # 30 dias
            self.validation_warnings.append(
                f"Tempo de expiração do token muito longo: {settings.ACCESS_TOKEN_EXPIRE_MINUTES} minutos"
            )
    
    def _validate_external_services_configuration(self):
        """Valida configuração de serviços externos."""
        logger.debug("🔍 Validando configuração de serviços externos")
        
        # Validar Evolution API
        if settings.EVOLUTION_API_URL:
            if not self._is_valid_url(settings.EVOLUTION_API_URL):
                self.validation_errors.append(
                    f"EVOLUTION_API_URL inválida: {settings.EVOLUTION_API_URL}"
                )
            elif self.is_production and self._is_localhost_url(settings.EVOLUTION_API_URL):
                self.validation_warnings.append(
                    "EVOLUTION_API_URL é localhost - verifique se é URL interna do EasyPanel"
                )
            else:
                logger.debug(f"✅ EVOLUTION_API_URL válida: {settings.EVOLUTION_API_URL}")
        
        # Validar Chatwoot
        if settings.CHATWOOT_URL:
            if not self._is_valid_url(settings.CHATWOOT_URL):
                self.validation_errors.append(
                    f"CHATWOOT_URL inválida: {settings.CHATWOOT_URL}"
                )
            elif self.is_production and self._is_localhost_url(settings.CHATWOOT_URL):
                self.validation_warnings.append(
                    "CHATWOOT_URL é localhost - verifique se é URL interna do EasyPanel"
                )
            else:
                logger.debug(f"✅ CHATWOOT_URL válida: {settings.CHATWOOT_URL}")
        
        # Validar token do Chatwoot
        if settings.CHATWOOT_ADMIN_TOKEN:
            if len(settings.CHATWOOT_ADMIN_TOKEN) < 10:
                self.validation_warnings.append(
                    "CHATWOOT_ADMIN_TOKEN parece muito curto"
                )
            else:
                logger.debug("✅ CHATWOOT_ADMIN_TOKEN tem comprimento adequado")
        
        # Validar OpenAI
        if settings.OPENAI_API_KEY:
            if not settings.OPENAI_API_KEY.startswith('sk-'):
                self.validation_errors.append(
                    "OPENAI_API_KEY deve começar com 'sk-'"
                )
            elif len(settings.OPENAI_API_KEY) < 40:
                self.validation_warnings.append(
                    "OPENAI_API_KEY parece muito curta"
                )
            else:
                logger.debug("✅ OPENAI_API_KEY tem formato válido")
        
        # Validar Redis
        if settings.REDIS_URL:
            if not self._is_valid_redis_url(settings.REDIS_URL):
                self.validation_errors.append(
                    f"REDIS_URL inválida: {settings.REDIS_URL}"
                )
            else:
                logger.debug(f"✅ REDIS_URL válida: {settings.REDIS_URL}")
    
    def _validate_cors_configuration(self):
        """Valida configuração CORS."""
        logger.debug("🔍 Validando configuração CORS")
        
        cors_origins = settings.cors_origins_list
        
        if self.is_production:
            if not cors_origins or cors_origins == ['*']:
                self.validation_errors.append(
                    "CORS deve ter origens específicas em produção, não '*'"
                )
            else:
                for origin in cors_origins:
                    if not self._is_valid_url(origin) and origin != '*':
                        self.validation_warnings.append(
                            f"Origem CORS inválida: {origin}"
                        )
                    elif self._is_localhost_url(origin):
                        self.validation_warnings.append(
                            f"Origem CORS localhost em produção: {origin}"
                        )
                logger.debug(f"✅ CORS configurado com {len(cors_origins)} origens")
        else:
            logger.debug("✅ CORS validação relaxada para desenvolvimento")
    
    def _validate_production_specific_settings(self):
        """Validações específicas para ambiente de produção."""
        logger.debug("🔍 Validando configurações específicas de produção")
        
        # Debug deve estar desabilitado
        if settings.DEBUG:
            self.validation_errors.append(
                "DEBUG deve ser False em produção"
            )
        else:
            logger.debug("✅ DEBUG desabilitado")
        
        # Verificar se não há URLs de desenvolvimento
        dev_indicators = ['localhost', '127.0.0.1', 'dev', 'test', 'staging']
        
        urls_to_check = {
            'SUPABASE_URL': settings.SUPABASE_URL,
            'EVOLUTION_API_URL': settings.EVOLUTION_API_URL,
            'CHATWOOT_URL': settings.CHATWOOT_URL,
        }
        
        for url_name, url_value in urls_to_check.items():
            if url_value:
                for indicator in dev_indicators:
                    if indicator in url_value.lower():
                        self.validation_warnings.append(
                            f"{url_name} contém indicador de desenvolvimento: {indicator}"
                        )
                        break
    
    def _is_valid_url(self, url: str) -> bool:
        """Verifica se uma URL é válida."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    def _is_localhost_url(self, url: str) -> bool:
        """Verifica se uma URL é localhost."""
        try:
            result = urlparse(url)
            return result.hostname in ['localhost', '127.0.0.1', '0.0.0.0']
        except Exception:
            return False
    
    def _is_valid_redis_url(self, url: str) -> bool:
        """Verifica se uma URL Redis é válida."""
        try:
            result = urlparse(url)
            return result.scheme in ['redis', 'rediss']
        except Exception:
            return False
    
    def _is_secure_secret(self, secret: str) -> bool:
        """
        Verifica se um secret é suficientemente seguro.
        
        Critérios:
        - Pelo menos 32 caracteres
        - Contém letras maiúsculas e minúsculas
        - Contém números
        - Contém caracteres especiais
        """
        if len(secret) < 32:
            return False
        
        has_upper = any(c.isupper() for c in secret)
        has_lower = any(c.islower() for c in secret)
        has_digit = any(c.isdigit() for c in secret)
        has_special = any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in secret)
        
        return has_upper and has_lower and has_digit and has_special
    
    def generate_secure_secret(self, length: int = 64) -> str:
        """Gera um secret seguro para uso em produção."""
        return secrets.token_urlsafe(length)
    
    def get_configuration_summary(self) -> Dict[str, Any]:
        """Retorna um resumo da configuração atual (sem secrets)."""
        return {
            'environment': self.environment,
            'is_production': self.is_production,
            'project_name': settings.PROJECT_NAME,
            'api_version': settings.API_V1_STR,
            'debug_enabled': settings.DEBUG,
            'jwt_algorithm': settings.JWT_ALGORITHM,
            'token_expire_minutes': settings.ACCESS_TOKEN_EXPIRE_MINUTES,
            'cors_origins_count': len(settings.cors_origins_list),
            'has_supabase_config': bool(settings.SUPABASE_URL and settings.SUPABASE_SERVICE_KEY),
            'has_openai_config': bool(settings.OPENAI_API_KEY),
            'has_evolution_config': bool(settings.EVOLUTION_API_URL and settings.EVOLUTION_API_KEY),
            'has_chatwoot_config': bool(settings.CHATWOOT_URL and settings.CHATWOOT_ADMIN_TOKEN),
            'openai_model': settings.OPENAI_MODEL,
            'agent_temperature': settings.AGENT_TEMPERATURE,
            'agent_memory_window': settings.AGENT_MEMORY_WINDOW,
        }
    
    def log_configuration_summary(self):
        """Registra um resumo da configuração nos logs."""
        summary = self.get_configuration_summary()
        
        logger.info("📋 Resumo da Configuração:")
        logger.info(f"  🌍 Ambiente: {summary['environment']}")
        logger.info(f"  🚀 Produção: {summary['is_production']}")
        logger.info(f"  📦 Projeto: {summary['project_name']}")
        logger.info(f"  🔧 Debug: {summary['debug_enabled']}")
        logger.info(f"  🔐 JWT: {summary['jwt_algorithm']}")
        logger.info(f"  ⏰ Token expira em: {summary['token_expire_minutes']} min")
        logger.info(f"  🌐 CORS origens: {summary['cors_origins_count']}")
        logger.info(f"  🗄️ Supabase: {'✅' if summary['has_supabase_config'] else '❌'}")
        logger.info(f"  🤖 OpenAI: {'✅' if summary['has_openai_config'] else '❌'}")
        logger.info(f"  📱 Evolution: {'✅' if summary['has_evolution_config'] else '❌'}")
        logger.info(f"  💬 Chatwoot: {'✅' if summary['has_chatwoot_config'] else '❌'}")

# Instância global do gerenciador de configuração
config_manager = ConfigurationManager()