"""
Middleware de logging para requests HTTP com correlation IDs e métricas.

Implementa:
- Correlation IDs automáticos para cada request
- Logging estruturado de requests/responses
- Métricas de performance
- Contexto de request para logs
"""

import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import (
    get_structured_logger, 
    correlation_id_var, 
    request_context_var,
    PerformanceLogger,
    AuditLogger
)

class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware para logging automático de requests com correlation IDs.
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.logger = get_structured_logger('request_middleware')
        self.performance_logger = PerformanceLogger()
        self.audit_logger = AuditLogger()
        
        # Endpoints que não devem ser logados (para evitar spam)
        self.skip_logging_paths = {
            '/health',
            '/api/v1/health',
            '/api/v1/health/detailed',
            '/docs',
            '/redoc',
            '/openapi.json'
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Gerar correlation ID
        correlation_id = request.headers.get('X-Correlation-ID') or str(uuid.uuid4())
        self.logger.with_correlation_id(correlation_id)
        
        # Extrair informações do request
        method = request.method
        path = request.url.path
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get('user-agent', 'unknown')
        
        # Configurar contexto de request
        self.logger.with_request_context(
            method=method,
            path=path,
            client_ip=client_ip,
            user_agent=user_agent
        )
        
        # Verificar se deve pular logging
        skip_detailed_logging = path in self.skip_logging_paths
        
        # Log de início do request (apenas para endpoints importantes)
        if not skip_detailed_logging:
            self.logger.info(
                f"Request started: {method} {path}",
                method=method,
                path=path,
                client_ip=client_ip,
                user_agent=user_agent,
                correlation_id=correlation_id
            )
        
        # Medir tempo de execução
        start_time = time.time()
        
        try:
            # Processar request
            response = await call_next(request)
            
            # Calcular duração
            duration_ms = (time.time() - start_time) * 1000
            
            # Adicionar correlation ID ao response
            response.headers['X-Correlation-ID'] = correlation_id
            
            # Log de conclusão do request
            if not skip_detailed_logging:
                self.logger.info(
                    f"Request completed: {method} {path} - {response.status_code} ({duration_ms:.0f}ms)",
                    method=method,
                    path=path,
                    status_code=response.status_code,
                    duration_ms=round(duration_ms, 2),
                    client_ip=client_ip,
                    correlation_id=correlation_id
                )
            
            # Log de performance
            self.performance_logger.log_request_duration(
                method=method,
                path=path,
                duration_ms=duration_ms,
                status_code=response.status_code,
                user_id=self._extract_user_id_from_request(request)
            )
            
            # Registrar métrica no dashboard (removido para evitar import circular)
            # record_request_metric(
            #     method=method,
            #     path=path,
            #     duration_ms=duration_ms,
            #     status_code=response.status_code,
            #     user_id=self._extract_user_id_from_request(request)
            # )
            
            # Log de auditoria para endpoints sensíveis
            if self._is_sensitive_endpoint(path):
                self.audit_logger.log_api_access(
                    endpoint=path,
                    method=method,
                    status_code=response.status_code,
                    user_id=self._extract_user_id_from_request(request),
                    client_ip=client_ip
                )
            
            return response
            
        except Exception as e:
            # Calcular duração mesmo em caso de erro
            duration_ms = (time.time() - start_time) * 1000
            
            # Log de erro
            self.logger.error(
                f"Request failed: {method} {path} - {str(e)} ({duration_ms:.0f}ms)",
                method=method,
                path=path,
                error=str(e),
                duration_ms=round(duration_ms, 2),
                client_ip=client_ip,
                correlation_id=correlation_id,
                exception=e
            )
            
            # Log de performance para erros
            self.performance_logger.log_request_duration(
                method=method,
                path=path,
                duration_ms=duration_ms,
                status_code=500,  # Assumir 500 para exceções não tratadas
                user_id=self._extract_user_id_from_request(request)
            )
            
            # Registrar métrica de erro no dashboard (removido para evitar import circular)
            # record_request_metric(
            #     method=method,
            #     path=path,
            #     duration_ms=duration_ms,
            #     status_code=500,
            #     user_id=self._extract_user_id_from_request(request)
            # )
            
            # Re-raise a exceção
            raise
    
    def _get_client_ip(self, request: Request) -> str:
        """Extrai o IP do cliente considerando proxies."""
        # Verificar headers de proxy
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            # Pegar o primeiro IP da lista (cliente original)
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
        
        # Fallback para IP direto
        if hasattr(request, 'client') and request.client:
            return request.client.host
        
        return 'unknown'
    
    def _extract_user_id_from_request(self, request: Request) -> str:
        """Tenta extrair user_id do request (JWT, headers, etc.)."""
        try:
            # Tentar extrair do header Authorization
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                # Aqui poderia decodificar o JWT para extrair o user_id
                # Por simplicidade, vamos usar um placeholder
                return 'from_jwt'
            
            # Tentar extrair de outros headers
            user_id = request.headers.get('X-User-ID')
            if user_id:
                return user_id
            
            return None
            
        except Exception:
            return None
    
    def _is_sensitive_endpoint(self, path: str) -> bool:
        """Verifica se o endpoint é sensível e requer auditoria."""
        sensitive_patterns = [
            '/api/v1/auth/',
            '/api/v1/tenants/',
            '/api/v1/agent/',
            '/api/v1/crm/',
            '/api/v1/knowledge/'
        ]
        
        return any(path.startswith(pattern) for pattern in sensitive_patterns)

class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware especializado para auditoria de segurança.
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.audit_logger = AuditLogger()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Detectar tentativas de acesso suspeitas
        await self._check_suspicious_activity(request)
        
        # Processar request normalmente
        response = await call_next(request)
        
        # Log de auditoria pós-processamento
        await self._log_post_request_audit(request, response)
        
        return response
    
    async def _check_suspicious_activity(self, request: Request):
        """Detecta atividades suspeitas no request."""
        path = request.url.path
        method = request.method
        client_ip = request.headers.get('X-Forwarded-For', 
                                       request.headers.get('X-Real-IP', 
                                                         getattr(request.client, 'host', 'unknown')))
        
        # Detectar tentativas de SQL injection
        query_params = str(request.query_params).lower()
        if any(pattern in query_params for pattern in ['union select', 'drop table', '1=1', 'or 1=1']):
            self.audit_logger.log_security_incident(
                incident_type='sql_injection_attempt',
                client_ip=client_ip,
                path=path,
                details={'query_params': str(request.query_params)}
            )
        
        # Detectar tentativas de path traversal
        if '../' in path or '..\\' in path:
            self.audit_logger.log_security_incident(
                incident_type='path_traversal_attempt',
                client_ip=client_ip,
                path=path,
                details={'attempted_path': path}
            )
        
        # Detectar requests com user-agents suspeitos
        user_agent = request.headers.get('user-agent', '').lower()
        suspicious_agents = ['sqlmap', 'nikto', 'nmap', 'masscan', 'nessus']
        if any(agent in user_agent for agent in suspicious_agents):
            self.audit_logger.log_security_incident(
                incident_type='suspicious_user_agent',
                client_ip=client_ip,
                path=path,
                details={'user_agent': user_agent}
            )
    
    async def _log_post_request_audit(self, request: Request, response: Response):
        """Log de auditoria após processamento do request."""
        # Log de tentativas de acesso negado
        if response.status_code in [401, 403]:
            self.audit_logger.log_access_denied(
                path=request.url.path,
                method=request.method,
                status_code=response.status_code,
                client_ip=self._get_client_ip(request),
                user_id=self._extract_user_id_from_request(request)
            )
        
        # Log de erros de servidor (possíveis ataques)
        elif response.status_code >= 500:
            self.audit_logger.log_server_error(
                path=request.url.path,
                method=request.method,
                status_code=response.status_code,
                client_ip=self._get_client_ip(request)
            )
    
    def _get_client_ip(self, request: Request) -> str:
        """Extrai o IP do cliente considerando proxies."""
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
        
        if hasattr(request, 'client') and request.client:
            return request.client.host
        
        return 'unknown'
    
    def _extract_user_id_from_request(self, request: Request) -> str:
        """Tenta extrair user_id do request."""
        try:
            user_id = request.headers.get('X-User-ID')
            if user_id:
                return user_id
            return None
        except Exception:
            return None

# Extensões para AuditLogger
class AuditLogger:
    """Extensão do AuditLogger com métodos específicos do middleware."""
    
    def __init__(self):
        from app.core.logging import get_structured_logger
        self.logger = get_structured_logger('security_audit')
    
    def log_security_incident(self, incident_type: str, client_ip: str, 
                             path: str, details: dict = None):
        """Log de incidente de segurança."""
        self.logger.error(
            f"Security incident detected: {incident_type}",
            incident_type=incident_type,
            client_ip=client_ip,
            path=path,
            details=details or {},
            severity='high'
        )
    
    def log_access_denied(self, path: str, method: str, status_code: int,
                         client_ip: str, user_id: str = None):
        """Log de acesso negado."""
        self.logger.warning(
            f"Access denied: {method} {path} - {status_code}",
            path=path,
            method=method,
            status_code=status_code,
            client_ip=client_ip,
            user_id=user_id,
            audit_type='access_denied'
        )
    
    def log_server_error(self, path: str, method: str, status_code: int,
                        client_ip: str):
        """Log de erro de servidor."""
        self.logger.error(
            f"Server error: {method} {path} - {status_code}",
            path=path,
            method=method,
            status_code=status_code,
            client_ip=client_ip,
            audit_type='server_error'
        )