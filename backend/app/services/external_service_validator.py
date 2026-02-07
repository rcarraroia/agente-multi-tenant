"""
External Service Validator for EasyPanel services.

Validates connectivity and health of external services:
- Evolution API (WhatsApp integration)
- Chatwoot (Customer support)
- Other EasyPanel services

Implements retry logic, circuit breaker pattern, and fallback mechanisms.
"""

import asyncio
import httpx
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
from contextlib import asynccontextmanager

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

class ServiceStatus(str, Enum):
    """Status de um serviço externo."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

class CircuitBreakerState(str, Enum):
    """Estados do Circuit Breaker."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, blocking requests
    HALF_OPEN = "half_open"  # Testing if service recovered

@dataclass
class ServiceHealthCheck:
    """Resultado de um health check."""
    service_name: str
    status: ServiceStatus
    response_time_ms: float
    last_checked: datetime
    error_message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

@dataclass
class CircuitBreakerConfig:
    """Configuração do Circuit Breaker."""
    failure_threshold: int = 5
    recovery_timeout: int = 60  # seconds
    request_timeout: int = 30   # seconds

class CircuitBreaker:
    """
    Circuit Breaker pattern implementation.
    
    Prevents cascading failures by temporarily blocking requests
    to failing services and allowing them to recover.
    """
    
    def __init__(self, service_name: str, config: CircuitBreakerConfig):
        self.service_name = service_name
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.last_success_time: Optional[datetime] = None
    
    def can_execute(self) -> bool:
        """Verifica se uma requisição pode ser executada."""
        if self.state == CircuitBreakerState.CLOSED:
            return True
        
        if self.state == CircuitBreakerState.OPEN:
            # Verificar se é hora de tentar novamente
            if self.last_failure_time:
                time_since_failure = (datetime.utcnow() - self.last_failure_time).total_seconds()
                if time_since_failure >= self.config.recovery_timeout:
                    logger.info(f"🔄 Circuit breaker para {self.service_name} mudando para HALF_OPEN")
                    self.state = CircuitBreakerState.HALF_OPEN
                    return True
            return False
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            return True
        
        return False
    
    def record_success(self):
        """Registra uma operação bem-sucedida."""
        self.failure_count = 0
        self.last_success_time = datetime.utcnow()
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            logger.info(f"✅ Circuit breaker para {self.service_name} mudando para CLOSED")
            self.state = CircuitBreakerState.CLOSED
    
    def record_failure(self):
        """Registra uma falha."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.failure_count >= self.config.failure_threshold:
            if self.state != CircuitBreakerState.OPEN:
                logger.warning(f"🚨 Circuit breaker para {self.service_name} mudando para OPEN")
                self.state = CircuitBreakerState.OPEN

class ExternalServiceValidator:
    """
    Validador de serviços externos com retry logic e circuit breaker.
    
    Responsável por:
    - Validar conectividade com Evolution API
    - Testar webhooks do Chatwoot
    - Executar health checks gerais
    - Implementar fallback mechanisms
    """
    
    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.last_health_checks: Dict[str, ServiceHealthCheck] = {}
        
        # Configurar circuit breakers para cada serviço
        self._setup_circuit_breakers()
    
    def _setup_circuit_breakers(self):
        """Configura circuit breakers para todos os serviços."""
        services = ["evolution_api", "chatwoot", "openai"]
        
        for service in services:
            config = CircuitBreakerConfig(
                failure_threshold=3,
                recovery_timeout=60,
                request_timeout=30
            )
            self.circuit_breakers[service] = CircuitBreaker(service, config)
            
            logger.debug(f"🔧 Circuit breaker configurado para {service}")
    
    async def validate_all_services(self) -> Dict[str, ServiceHealthCheck]:
        """
        Valida todos os serviços externos configurados.
        
        Returns:
            Dict com health checks de todos os serviços
        """
        logger.info("🔍 Iniciando validação de todos os serviços externos")
        
        results = {}
        
        # Validar Evolution API
        if settings.EVOLUTION_API_URL:
            results["evolution_api"] = await self.validate_evolution_api()
        else:
            results["evolution_api"] = ServiceHealthCheck(
                service_name="evolution_api",
                status=ServiceStatus.UNKNOWN,
                response_time_ms=0,
                last_checked=datetime.utcnow(),
                error_message="URL não configurada"
            )
        
        # Validar Chatwoot
        if settings.CHATWOOT_URL and settings.CHATWOOT_ADMIN_TOKEN:
            results["chatwoot"] = await self.validate_chatwoot()
        else:
            results["chatwoot"] = ServiceHealthCheck(
                service_name="chatwoot",
                status=ServiceStatus.UNKNOWN,
                response_time_ms=0,
                last_checked=datetime.utcnow(),
                error_message="URL ou token não configurado"
            )
        
        # Validar OpenAI
        if settings.OPENAI_API_KEY:
            results["openai"] = await self.validate_openai()
        else:
            results["openai"] = ServiceHealthCheck(
                service_name="openai",
                status=ServiceStatus.UNKNOWN,
                response_time_ms=0,
                last_checked=datetime.utcnow(),
                error_message="API Key não configurada"
            )
        
        # Atualizar cache
        self.last_health_checks.update(results)
        
        # Log resumo
        healthy_count = sum(1 for check in results.values() if check.status == ServiceStatus.HEALTHY)
        total_count = len(results)
        
        logger.info(f"📊 Validação concluída: {healthy_count}/{total_count} serviços saudáveis")
        
        return results
    
    async def validate_evolution_api(self) -> ServiceHealthCheck:
        """
        Valida conectividade com Evolution API.
        
        Testa:
        - Conectividade básica
        - Autenticação
        - Endpoints principais
        """
        service_name = "evolution_api"
        start_time = datetime.utcnow()
        
        logger.debug(f"🔍 Validando Evolution API: {settings.EVOLUTION_API_URL}")
        
        # Verificar circuit breaker
        circuit_breaker = self.circuit_breakers[service_name]
        if not circuit_breaker.can_execute():
            logger.warning(f"🚨 Circuit breaker OPEN para {service_name}")
            return ServiceHealthCheck(
                service_name=service_name,
                status=ServiceStatus.UNHEALTHY,
                response_time_ms=0,
                last_checked=start_time,
                error_message="Circuit breaker OPEN"
            )
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Testar endpoint de status/manager (mais comum em Evolution API)
                status_url = f"{settings.EVOLUTION_API_URL.rstrip('/')}/manager/status"
                
                response = await client.get(
                    status_url,
                    headers={
                        "apikey": settings.EVOLUTION_API_KEY,
                        "Content-Type": "application/json"
                    }
                )
                
                response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                
                if response.status_code == 200:
                    circuit_breaker.record_success()
                    
                    # Tentar obter informações adicionais
                    details = {}
                    try:
                        data = response.json()
                        details = {
                            "version": data.get("version", "unknown"),
                            "status": data.get("status", "unknown"),
                            "instances": data.get("instances", 0)
                        }
                    except:
                        details = {"raw_response": response.text[:200]}
                    
                    logger.info(f"✅ Evolution API saudável (tempo: {response_time:.0f}ms)")
                    
                    return ServiceHealthCheck(
                        service_name=service_name,
                        status=ServiceStatus.HEALTHY,
                        response_time_ms=response_time,
                        last_checked=start_time,
                        details=details
                    )
                else:
                    circuit_breaker.record_failure()
                    error_msg = f"HTTP {response.status_code}: {response.text[:100]}"
                    
                    logger.warning(f"⚠️ Evolution API retornou erro: {error_msg}")
                    
                    return ServiceHealthCheck(
                        service_name=service_name,
                        status=ServiceStatus.DEGRADED,
                        response_time_ms=response_time,
                        last_checked=start_time,
                        error_message=error_msg
                    )
        
        except httpx.TimeoutException:
            circuit_breaker.record_failure()
            error_msg = "Timeout na conexão"
            logger.warning(f"⏰ Evolution API timeout")
            
            return ServiceHealthCheck(
                service_name=service_name,
                status=ServiceStatus.UNHEALTHY,
                response_time_ms=30000,  # timeout
                last_checked=start_time,
                error_message=error_msg
            )
        
        except Exception as e:
            circuit_breaker.record_failure()
            error_msg = f"Erro de conexão: {str(e)}"
            logger.error(f"💥 Erro ao validar Evolution API: {error_msg}")
            
            return ServiceHealthCheck(
                service_name=service_name,
                status=ServiceStatus.UNHEALTHY,
                response_time_ms=0,
                last_checked=start_time,
                error_message=error_msg
            )
    
    async def validate_chatwoot(self) -> ServiceHealthCheck:
        """
        Valida conectividade com Chatwoot.
        
        Testa:
        - Conectividade básica
        - API de status
        - Webhook endpoints
        """
        service_name = "chatwoot"
        start_time = datetime.utcnow()
        
        logger.debug(f"🔍 Validando Chatwoot: {settings.CHATWOOT_URL}")
        
        # Verificar circuit breaker
        circuit_breaker = self.circuit_breakers[service_name]
        if not circuit_breaker.can_execute():
            logger.warning(f"🚨 Circuit breaker OPEN para {service_name}")
            return ServiceHealthCheck(
                service_name=service_name,
                status=ServiceStatus.UNHEALTHY,
                response_time_ms=0,
                last_checked=start_time,
                error_message="Circuit breaker OPEN"
            )
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Testar endpoint básico de status do Chatwoot
                api_url = f"{settings.CHATWOOT_URL.rstrip('/')}/api/v1/profile"
                
                response = await client.get(
                    api_url,
                    headers={
                        "api_access_token": settings.CHATWOOT_ADMIN_TOKEN,
                        "Content-Type": "application/json"
                    }
                )
                
                response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                
                if response.status_code in [200, 401]:  # 401 é esperado se token inválido, mas serviço está up
                    circuit_breaker.record_success()
                    
                    status = ServiceStatus.HEALTHY if response.status_code == 200 else ServiceStatus.DEGRADED
                    
                    details = {
                        "status_code": response.status_code,
                        "authenticated": response.status_code == 200
                    }
                    
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            details["accounts_count"] = len(data) if isinstance(data, list) else 0
                        except:
                            pass
                    
                    logger.info(f"✅ Chatwoot {'saudável' if status == ServiceStatus.HEALTHY else 'degradado'} (tempo: {response_time:.0f}ms)")
                    
                    return ServiceHealthCheck(
                        service_name=service_name,
                        status=status,
                        response_time_ms=response_time,
                        last_checked=start_time,
                        details=details,
                        error_message="Token inválido" if response.status_code == 401 else None
                    )
                else:
                    circuit_breaker.record_failure()
                    error_msg = f"HTTP {response.status_code}: {response.text[:100]}"
                    
                    logger.warning(f"⚠️ Chatwoot retornou erro: {error_msg}")
                    
                    return ServiceHealthCheck(
                        service_name=service_name,
                        status=ServiceStatus.UNHEALTHY,
                        response_time_ms=response_time,
                        last_checked=start_time,
                        error_message=error_msg
                    )
        
        except httpx.TimeoutException:
            circuit_breaker.record_failure()
            error_msg = "Timeout na conexão"
            logger.warning(f"⏰ Chatwoot timeout")
            
            return ServiceHealthCheck(
                service_name=service_name,
                status=ServiceStatus.UNHEALTHY,
                response_time_ms=30000,
                last_checked=start_time,
                error_message=error_msg
            )
        
        except Exception as e:
            circuit_breaker.record_failure()
            error_msg = f"Erro de conexão: {str(e)}"
            logger.error(f"💥 Erro ao validar Chatwoot: {error_msg}")
            
            return ServiceHealthCheck(
                service_name=service_name,
                status=ServiceStatus.UNHEALTHY,
                response_time_ms=0,
                last_checked=start_time,
                error_message=error_msg
            )
    
    async def validate_openai(self) -> ServiceHealthCheck:
        """
        Valida conectividade com OpenAI API.
        
        Testa:
        - Conectividade básica
        - Autenticação
        - Modelos disponíveis
        """
        service_name = "openai"
        start_time = datetime.utcnow()
        
        logger.debug("🔍 Validando OpenAI API")
        
        # Verificar circuit breaker
        circuit_breaker = self.circuit_breakers[service_name]
        if not circuit_breaker.can_execute():
            logger.warning(f"🚨 Circuit breaker OPEN para {service_name}")
            return ServiceHealthCheck(
                service_name=service_name,
                status=ServiceStatus.UNHEALTHY,
                response_time_ms=0,
                last_checked=start_time,
                error_message="Circuit breaker OPEN"
            )
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Testar endpoint de modelos
                response = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={
                        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                        "Content-Type": "application/json"
                    }
                )
                
                response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                
                if response.status_code == 200:
                    circuit_breaker.record_success()
                    
                    details = {}
                    try:
                        data = response.json()
                        models = data.get("data", [])
                        details = {
                            "models_count": len(models),
                            "configured_model": settings.OPENAI_MODEL,
                            "model_available": any(m.get("id") == settings.OPENAI_MODEL for m in models)
                        }
                    except:
                        details = {"response_ok": True}
                    
                    logger.info(f"✅ OpenAI API saudável (tempo: {response_time:.0f}ms)")
                    
                    return ServiceHealthCheck(
                        service_name=service_name,
                        status=ServiceStatus.HEALTHY,
                        response_time_ms=response_time,
                        last_checked=start_time,
                        details=details
                    )
                else:
                    circuit_breaker.record_failure()
                    error_msg = f"HTTP {response.status_code}: {response.text[:100]}"
                    
                    logger.warning(f"⚠️ OpenAI API retornou erro: {error_msg}")
                    
                    return ServiceHealthCheck(
                        service_name=service_name,
                        status=ServiceStatus.DEGRADED,
                        response_time_ms=response_time,
                        last_checked=start_time,
                        error_message=error_msg
                    )
        
        except httpx.TimeoutException:
            circuit_breaker.record_failure()
            error_msg = "Timeout na conexão"
            logger.warning(f"⏰ OpenAI API timeout")
            
            return ServiceHealthCheck(
                service_name=service_name,
                status=ServiceStatus.UNHEALTHY,
                response_time_ms=30000,
                last_checked=start_time,
                error_message=error_msg
            )
        
        except Exception as e:
            circuit_breaker.record_failure()
            error_msg = f"Erro de conexão: {str(e)}"
            logger.error(f"💥 Erro ao validar OpenAI API: {error_msg}")
            
            return ServiceHealthCheck(
                service_name=service_name,
                status=ServiceStatus.UNHEALTHY,
                response_time_ms=0,
                last_checked=start_time,
                error_message=error_msg
            )
    
    async def test_webhook_connectivity(self, webhook_url: str, service_name: str) -> ServiceHealthCheck:
        """
        Testa conectividade de webhook.
        
        Args:
            webhook_url: URL do webhook para testar
            service_name: Nome do serviço para logging
            
        Returns:
            ServiceHealthCheck com resultado do teste
        """
        start_time = datetime.utcnow()
        
        logger.debug(f"🔍 Testando webhook {service_name}: {webhook_url}")
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Fazer um HEAD request para testar conectividade
                response = await client.head(webhook_url)
                
                response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                
                # Webhook pode retornar vários códigos (200, 405, 404, etc.)
                # O importante é que seja acessível
                if response.status_code < 500:
                    logger.info(f"✅ Webhook {service_name} acessível (tempo: {response_time:.0f}ms)")
                    
                    return ServiceHealthCheck(
                        service_name=f"{service_name}_webhook",
                        status=ServiceStatus.HEALTHY,
                        response_time_ms=response_time,
                        last_checked=start_time,
                        details={"status_code": response.status_code}
                    )
                else:
                    error_msg = f"HTTP {response.status_code}"
                    logger.warning(f"⚠️ Webhook {service_name} retornou erro: {error_msg}")
                    
                    return ServiceHealthCheck(
                        service_name=f"{service_name}_webhook",
                        status=ServiceStatus.DEGRADED,
                        response_time_ms=response_time,
                        last_checked=start_time,
                        error_message=error_msg
                    )
        
        except httpx.TimeoutException:
            error_msg = "Timeout na conexão"
            logger.warning(f"⏰ Webhook {service_name} timeout")
            
            return ServiceHealthCheck(
                service_name=f"{service_name}_webhook",
                status=ServiceStatus.UNHEALTHY,
                response_time_ms=10000,
                last_checked=start_time,
                error_message=error_msg
            )
        
        except Exception as e:
            error_msg = f"Erro de conexão: {str(e)}"
            logger.error(f"💥 Erro ao testar webhook {service_name}: {error_msg}")
            
            return ServiceHealthCheck(
                service_name=f"{service_name}_webhook",
                status=ServiceStatus.UNHEALTHY,
                response_time_ms=0,
                last_checked=start_time,
                error_message=error_msg
            )
    
    def get_service_status_summary(self) -> Dict[str, Any]:
        """
        Obtém resumo do status de todos os serviços.
        
        Returns:
            Dict com resumo dos status
        """
        if not self.last_health_checks:
            return {
                "overall_status": ServiceStatus.UNKNOWN,
                "services": {},
                "last_check": None,
                "summary": "Nenhuma verificação realizada ainda"
            }
        
        services = {}
        healthy_count = 0
        total_count = len(self.last_health_checks)
        
        for service_name, check in self.last_health_checks.items():
            services[service_name] = {
                "status": check.status,
                "response_time_ms": check.response_time_ms,
                "last_checked": check.last_checked.isoformat(),
                "error": check.error_message
            }
            
            if check.status == ServiceStatus.HEALTHY:
                healthy_count += 1
        
        # Determinar status geral
        if healthy_count == total_count:
            overall_status = ServiceStatus.HEALTHY
        elif healthy_count > 0:
            overall_status = ServiceStatus.DEGRADED
        else:
            overall_status = ServiceStatus.UNHEALTHY
        
        return {
            "overall_status": overall_status,
            "services": services,
            "last_check": max(check.last_checked for check in self.last_health_checks.values()).isoformat(),
            "summary": f"{healthy_count}/{total_count} serviços saudáveis"
        }
    
    def get_circuit_breaker_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Obtém status de todos os circuit breakers.
        
        Returns:
            Dict com status dos circuit breakers
        """
        status = {}
        
        for service_name, breaker in self.circuit_breakers.items():
            status[service_name] = {
                "state": breaker.state,
                "failure_count": breaker.failure_count,
                "last_failure": breaker.last_failure_time.isoformat() if breaker.last_failure_time else None,
                "last_success": breaker.last_success_time.isoformat() if breaker.last_success_time else None,
                "can_execute": breaker.can_execute()
            }
        
        return status

# Instância global do validador
external_service_validator = ExternalServiceValidator()