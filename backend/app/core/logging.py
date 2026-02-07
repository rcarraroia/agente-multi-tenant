"""
Sistema de Logging Estruturado para Agente Multi-Tenant

Implementa logging com contexto de tenant, correlation IDs, performance monitoring
e auditoria para debugging e monitoramento em produção.
"""

import logging
import json
import uuid
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID
from contextvars import ContextVar
import time

from app.config import settings

# Context variables para correlation ID e request context
correlation_id_var: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)
request_context_var: ContextVar[Optional[Dict[str, Any]]] = ContextVar('request_context', default=None)


class StructuredLogger:
    """
    Logger estruturado com correlation IDs e contexto de request.
    
    Fornece logging estruturado com:
    - Correlation IDs automáticos
    - Contexto de request
    - Métricas de performance
    - Logs de auditoria
    """
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.name = name
    
    def _get_base_context(self) -> Dict[str, Any]:
        """Obtém contexto base para todos os logs."""
        context = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'module': self.name,
            'correlation_id': correlation_id_var.get(),
        }
        
        # Adicionar contexto de request se disponível
        request_context = request_context_var.get()
        if request_context:
            context.update(request_context)
        
        return context
    
    def with_correlation_id(self, correlation_id: str):
        """Define correlation ID para este logger."""
        correlation_id_var.set(correlation_id)
        return self
    
    def with_request_context(self, **kwargs):
        """Define contexto de request para este logger."""
        request_context_var.set(kwargs)
        return self
    
    def debug(self, message: str, **kwargs):
        """Log de debug estruturado."""
        context = self._get_base_context()
        context.update(kwargs)
        context['level'] = 'DEBUG'
        context['message'] = message
        
        self.logger.debug(json.dumps(context, ensure_ascii=False))
    
    def info(self, message: str, **kwargs):
        """Log de info estruturado."""
        context = self._get_base_context()
        context.update(kwargs)
        context['level'] = 'INFO'
        context['message'] = message
        
        self.logger.info(json.dumps(context, ensure_ascii=False))
    
    def warning(self, message: str, **kwargs):
        """Log de warning estruturado."""
        context = self._get_base_context()
        context.update(kwargs)
        context['level'] = 'WARNING'
        context['message'] = message
        
        self.logger.warning(json.dumps(context, ensure_ascii=False))
    
    def error(self, message: str, exception: Exception = None, **kwargs):
        """Log de error estruturado."""
        context = self._get_base_context()
        context.update(kwargs)
        context['level'] = 'ERROR'
        context['message'] = message
        
        if exception:
            context['exception'] = {
                'type': type(exception).__name__,
                'message': str(exception),
                'traceback': str(exception.__traceback__) if exception.__traceback__ else None
            }
        
        self.logger.error(json.dumps(context, ensure_ascii=False))

class PerformanceLogger:
    """
    Logger especializado para métricas de performance.
    """
    
    def __init__(self):
        self.logger = get_structured_logger('performance')
    
    def log_request_duration(self, method: str, path: str, duration_ms: float, 
                           status_code: int, user_id: str = None):
        """Log de duração de request."""
        self.logger.info(
            f"Request performance: {method} {path}",
            metric_type='request_duration',
            method=method,
            path=path,
            duration_ms=duration_ms,
            status_code=status_code,
            user_id=user_id,
            performance=True
        )
    
    def log_database_query(self, query_type: str, table: str, duration_ms: float, 
                          rows_affected: int = None):
        """Log de performance de query de banco."""
        self.logger.info(
            f"Database query: {query_type} on {table}",
            metric_type='database_query',
            query_type=query_type,
            table=table,
            duration_ms=duration_ms,
            rows_affected=rows_affected,
            performance=True
        )
    
    def log_external_service_call(self, service: str, operation: str, 
                                 duration_ms: float, success: bool):
        """Log de chamada para serviço externo."""
        self.logger.info(
            f"External service call: {service}.{operation}",
            metric_type='external_service_call',
            service=service,
            operation=operation,
            duration_ms=duration_ms,
            success=success,
            performance=True
        )

class AuditLogger:
    """
    Logger especializado para auditoria de segurança e ações de usuário.
    """
    
    def __init__(self):
        self.logger = get_structured_logger('audit')
    
    def log_api_access(self, endpoint: str, method: str, status_code: int,
                      user_id: str = None, client_ip: str = None):
        """Log de acesso a API."""
        self.logger.info(
            f"API access: {method} {endpoint}",
            audit_type='api_access',
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            user_id=user_id,
            client_ip=client_ip,
            audit=True
        )
    
    def log_user_action(self, action: str, user_id: str, resource: str = None,
                       details: Dict[str, Any] = None):
        """Log de ação de usuário."""
        self.logger.info(
            f"User action: {action}",
            audit_type='user_action',
            action=action,
            user_id=user_id,
            resource=resource,
            details=details or {},
            audit=True
        )
    
class TenantContextFilter(logging.Filter):
    """
    Filtro para adicionar contexto de tenant aos logs.
    """
    
    def __init__(self):
        super().__init__()
        self.tenant_id: Optional[str] = None
        self.affiliate_id: Optional[str] = None
        self.user_id: Optional[str] = None
    
    def filter(self, record):
        # Adicionar contexto de tenant ao record
        record.tenant_id = getattr(self, 'tenant_id', None)
        record.affiliate_id = getattr(self, 'affiliate_id', None)
        record.user_id = getattr(self, 'user_id', None)
        return True
    
    def set_context(self, tenant_id: Optional[str] = None, 
                   affiliate_id: Optional[str] = None,
                   user_id: Optional[str] = None):
        """Define contexto atual para os logs."""
        self.tenant_id = tenant_id
        self.affiliate_id = affiliate_id
        self.user_id = user_id
    """
    Filtro para adicionar contexto de tenant aos logs.
    """
    
    def __init__(self):
        super().__init__()
        self.tenant_id: Optional[str] = None
        self.affiliate_id: Optional[str] = None
        self.user_id: Optional[str] = None
    
    def filter(self, record):
        # Adicionar contexto de tenant ao record
        record.tenant_id = getattr(self, 'tenant_id', None)
        record.affiliate_id = getattr(self, 'affiliate_id', None)
        record.user_id = getattr(self, 'user_id', None)
        return True
    
    def set_context(self, tenant_id: Optional[str] = None, 
                   affiliate_id: Optional[str] = None,
                   user_id: Optional[str] = None):
        """Define contexto atual para os logs."""
        self.tenant_id = tenant_id
        self.affiliate_id = affiliate_id
        self.user_id = user_id


class StructuredFormatter(logging.Formatter):
    """
    Formatter para logs estruturados em JSON.
    """
    
    def format(self, record):
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'module': record.name,
            'message': record.getMessage(),
            'tenant_id': getattr(record, 'tenant_id', None),
            'affiliate_id': getattr(record, 'affiliate_id', None),
            'user_id': getattr(record, 'user_id', None),
        }
        
        # Adicionar informações extras se disponíveis
        if hasattr(record, 'extra_data'):
            log_data.update(record.extra_data)
        
        # Adicionar stack trace se for erro
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False)


# Configurar logger global
def setup_logging():
    """
    Configura o sistema de logging da aplicação.
    """
    # Criar logger principal
    logger = logging.getLogger('agente_multi_tenant')
    logger.setLevel(logging.INFO if settings.ENVIRONMENT == 'production' else logging.DEBUG)
    
    # Remover handlers existentes
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Criar handler para console
    console_handler = logging.StreamHandler()
    
    # Configurar formatter
    if settings.ENVIRONMENT == 'production':
        formatter = StructuredFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [T:%(tenant_id)s|A:%(affiliate_id)s] - %(message)s'
        )
    
    console_handler.setFormatter(formatter)
    
    # Adicionar filtro de contexto
    context_filter = TenantContextFilter()
    console_handler.addFilter(context_filter)
    
    # Adicionar handler ao logger
    logger.addHandler(console_handler)
    
    return logger, context_filter


# Instância global
logger, context_filter = setup_logging()


def get_logger(name: str = 'agente_multi_tenant') -> logging.Logger:
    """
    Retorna logger tradicional (compatibilidade).
    
    Args:
        name: Nome do módulo/componente
        
    Returns:
        Logger tradicional configurado
    """
    return logging.getLogger(name)

def get_structured_logger(name: str = 'agente_multi_tenant') -> StructuredLogger:
    """
    Retorna logger estruturado configurado.
    
    Args:
        name: Nome do módulo/componente
        
    Returns:
        StructuredLogger configurado
    """
    return StructuredLogger(name)


def set_tenant_context(tenant_id: Optional[UUID] = None,
                      affiliate_id: Optional[UUID] = None,
                      user_id: Optional[str] = None):
    """
    Define contexto de tenant para os logs.
    
    Args:
        tenant_id: ID do tenant
        affiliate_id: ID do afiliado
        user_id: ID do usuário
    """
    context_filter.set_context(
        tenant_id=str(tenant_id) if tenant_id else None,
        affiliate_id=str(affiliate_id) if affiliate_id else None,
        user_id=user_id
    )


def log_tenant_resolution(user_id: str, affiliate_id: UUID, tenant_id: UUID, 
                         success: bool = True, error: Optional[str] = None):
    """
    Log específico para resolução de tenant.
    
    Args:
        user_id: ID do usuário
        affiliate_id: ID do afiliado
        tenant_id: ID do tenant
        success: Se a resolução foi bem-sucedida
        error: Mensagem de erro se houver
    """
    logger = get_logger('tenant_resolver')
    
    extra_data = {
        'action': 'tenant_resolution',
        'user_id': user_id,
        'affiliate_id': str(affiliate_id),
        'tenant_id': str(tenant_id),
        'success': success
    }
    
    if error:
        extra_data['error'] = error
    
    if success:
        logger.info(
            f"Tenant resolvido com sucesso: user_id={user_id} -> tenant_id={tenant_id}",
            extra={'extra_data': extra_data}
        )
    else:
        logger.error(
            f"Falha na resolução de tenant: user_id={user_id} - {error}",
            extra={'extra_data': extra_data}
        )


def log_subscription_check(affiliate_id: UUID, has_subscription: bool, 
                          service_type: str = 'agente_ia'):
    """
    Log específico para verificação de assinatura.
    
    Args:
        affiliate_id: ID do afiliado
        has_subscription: Se tem assinatura ativa
        service_type: Tipo de serviço verificado
    """
    logger = get_logger('subscription_checker')
    
    extra_data = {
        'action': 'subscription_check',
        'affiliate_id': str(affiliate_id),
        'service_type': service_type,
        'has_subscription': has_subscription
    }
    
    if has_subscription:
        logger.info(
            f"Assinatura ativa confirmada: affiliate_id={affiliate_id} service={service_type}",
            extra={'extra_data': extra_data}
        )
    else:
        logger.warning(
            f"Assinatura inativa ou expirada: affiliate_id={affiliate_id} service={service_type}",
            extra={'extra_data': extra_data}
        )


def log_api_access(endpoint: str, method: str, user_id: Optional[str] = None,
                  tenant_id: Optional[UUID] = None, status_code: Optional[int] = None):
    """
    Log específico para acesso a APIs.
    
    Args:
        endpoint: Endpoint acessado
        method: Método HTTP
        user_id: ID do usuário
        tenant_id: ID do tenant
        status_code: Código de resposta HTTP
    """
    logger = get_logger('api_access')
    
    extra_data = {
        'action': 'api_access',
        'endpoint': endpoint,
        'method': method,
        'user_id': user_id,
        'tenant_id': str(tenant_id) if tenant_id else None,
        'status_code': status_code
    }
    
    logger.info(
        f"API Access: {method} {endpoint} - Status: {status_code}",
        extra={'extra_data': extra_data}
    )