"""
Health check endpoints with external service validation.

Provides comprehensive health monitoring including:
- Application health
- External services status
- Circuit breaker status
- System metrics
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Dict, Any, List
from datetime import datetime
import time
import httpx

from app.services.external_service_validator import external_service_validator, ServiceStatus
from app.core.logging import get_logger
from app.core.database import get_supabase
from app.config import settings

logger = get_logger(__name__)
router = APIRouter()

# Tempo de inicialização da aplicação
startup_time = datetime.utcnow()

async def check_services_health() -> Dict[str, Any]:
    """Verifica saúde real dos serviços externos."""
    services = {}
    
    # Check Supabase
    try:
        start_time = time.time()
        supabase = get_supabase()
        result = supabase.table('multi_agent_tenants').select('id').limit(1).execute()
        duration_ms = (time.time() - start_time) * 1000
        
        services['supabase'] = {
            'status': 'healthy',
            'response_time_ms': round(duration_ms, 2),
            'message': 'Database connection successful'
        }
    except Exception as e:
        services['supabase'] = {
            'status': 'unhealthy',
            'error': str(e),
            'message': 'Database connection failed'
        }
    
    # Check Evolution API
    if settings.EVOLUTION_API_URL:
        try:
            start_time = time.time()
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{settings.EVOLUTION_API_URL}/health")
                duration_ms = (time.time() - start_time) * 1000
                
                services['evolution_api'] = {
                    'status': 'healthy' if response.status_code == 200 else 'degraded',
                    'response_time_ms': round(duration_ms, 2),
                    'status_code': response.status_code,
                    'message': 'Evolution API accessible'
                }
        except Exception as e:
            services['evolution_api'] = {
                'status': 'unhealthy',
                'error': str(e),
                'message': 'Evolution API connection failed'
            }
    else:
        services['evolution_api'] = {
            'status': 'not_configured',
            'message': 'Evolution API URL not configured'
        }
    
    # Check Chatwoot
    if settings.CHATWOOT_URL:
        try:
            start_time = time.time()
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{settings.CHATWOOT_URL}/api/v1/accounts")
                duration_ms = (time.time() - start_time) * 1000
                
                services['chatwoot'] = {
                    'status': 'healthy' if response.status_code == 200 else 'degraded',
                    'response_time_ms': round(duration_ms, 2),
                    'status_code': response.status_code,
                    'message': 'Chatwoot API accessible'
                }
        except Exception as e:
            services['chatwoot'] = {
                'status': 'unhealthy',
                'error': str(e),
                'message': 'Chatwoot API connection failed'
            }
    else:
        services['chatwoot'] = {
            'status': 'not_configured',
            'message': 'Chatwoot URL not configured'
        }
    
    return services

class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str
    timestamp: datetime
    version: str = "1.0.0"
    environment: str
    uptime_seconds: float
    services: Dict[str, Any]
    circuit_breakers: Dict[str, Any]

class DetailedHealthResponse(BaseModel):
    """Detailed health response with full service information."""
    status: str
    timestamp: datetime
    version: str = "1.0.0"
    environment: str
    uptime_seconds: float
    services: Dict[str, Any]
    circuit_breakers: Dict[str, Any]
    configuration: Dict[str, Any]
    metrics: Dict[str, Any]

# Startup time for uptime calculation
startup_time = datetime.utcnow()

@router.get("/", response_model=HealthResponse)
async def health_check():
    """
    Basic health check endpoint.
    
    Returns application status and external services summary.
    """
    try:
        logger.debug("🔍 Health check solicitado")
        
        # Calcular uptime
        uptime = (datetime.utcnow() - startup_time).total_seconds()
        
        # Verificar serviços reais
        services_status = await check_services_health()
        
        # Determinar status geral
        overall_status = "healthy"
        if any(service.get("status") == "unhealthy" for service in services_status.values()):
            overall_status = "degraded"
        
        # Resposta com verificação real
        response = HealthResponse(
            status=overall_status,
            timestamp=datetime.utcnow(),
            environment=settings.ENVIRONMENT,
            uptime_seconds=uptime,
            services=services_status,
            circuit_breakers={"status": "ok", "message": "Circuit breakers operational"}
        )
        
        logger.debug(f"✅ Health check concluído: {overall_status}")
        
        return response
        
    except Exception as e:
        logger.error(f"💥 Erro no health check: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Erro interno no health check",
                "error": str(e)
            }
        )

@router.get("/health/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check():
    """
    Detailed health check with full system information.
    
    Includes configuration, metrics, and comprehensive service status.
    """
    try:
        logger.debug("🔍 Health check detalhado solicitado")
        
        # Calcular uptime
        uptime = (datetime.utcnow() - startup_time).total_seconds()
        
        # Executar validação completa de serviços
        services_checks = await external_service_validator.validate_all_services()
        
        # Obter status dos circuit breakers
        circuit_breakers_status = external_service_validator.get_circuit_breaker_status()
        
        # Preparar informações de configuração (sem dados sensíveis)
        configuration = {
            "environment": settings.ENVIRONMENT,
            "debug": settings.DEBUG,
            "cors_origins_configured": len(settings.cors_origins_list) > 0,
            "external_services": {
                "evolution_api_configured": bool(settings.EVOLUTION_API_URL),
                "chatwoot_configured": bool(settings.CHATWOOT_URL),
                "openai_configured": bool(settings.OPENAI_API_KEY),
                "supabase_configured": bool(settings.SUPABASE_URL)
            }
        }
        
        # Preparar métricas básicas
        metrics = {
            "uptime_seconds": uptime,
            "uptime_human": _format_uptime(uptime),
            "services_count": len(services_checks),
            "healthy_services": sum(1 for check in services_checks.values() if check.status == ServiceStatus.HEALTHY),
            "circuit_breakers_open": sum(1 for cb in circuit_breakers_status.values() if cb["state"] == "open")
        }
        
        # Determinar status geral
        healthy_count = metrics["healthy_services"]
        total_count = metrics["services_count"]
        
        if healthy_count == total_count:
            overall_status = "healthy"
        elif healthy_count > 0:
            overall_status = "degraded"
        else:
            overall_status = "unhealthy"
        
        # Preparar dados dos serviços
        services_data = {}
        for service_name, check in services_checks.items():
            services_data[service_name] = {
                "status": check.status,
                "response_time_ms": check.response_time_ms,
                "last_checked": check.last_checked.isoformat(),
                "error_message": check.error_message,
                "details": check.details
            }
        
        response = DetailedHealthResponse(
            status=overall_status,
            timestamp=datetime.utcnow(),
            environment=settings.ENVIRONMENT,
            uptime_seconds=uptime,
            services={
                "summary": f"{healthy_count}/{total_count} services healthy",
                "details": services_data
            },
            circuit_breakers=circuit_breakers_status,
            configuration=configuration,
            metrics=metrics
        )
        
        logger.info(f"✅ Health check detalhado concluído: {overall_status}")
        logger.info(f"   Serviços: {healthy_count}/{total_count} saudáveis")
        logger.info(f"   Circuit breakers abertos: {metrics['circuit_breakers_open']}")
        
        return response
        
    except Exception as e:
        logger.error(f"💥 Erro no health check detalhado: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Erro interno no health check detalhado",
                "error": str(e)
            }
        )

@router.post("/health/validate")
async def validate_external_services():
    """
    Force validation of all external services.
    
    Triggers immediate health checks for all configured services.
    """
    try:
        logger.info("🔄 Validação forçada de serviços externos solicitada")
        
        # Executar validação completa
        services_checks = await external_service_validator.validate_all_services()
        
        # Preparar resposta
        results = {}
        for service_name, check in services_checks.items():
            results[service_name] = {
                "status": check.status,
                "response_time_ms": check.response_time_ms,
                "error_message": check.error_message,
                "last_checked": check.last_checked.isoformat()
            }
        
        healthy_count = sum(1 for check in services_checks.values() if check.status == ServiceStatus.HEALTHY)
        total_count = len(services_checks)
        
        logger.info(f"✅ Validação forçada concluída: {healthy_count}/{total_count} serviços saudáveis")
        
        return {
            "message": "Validação de serviços externos concluída",
            "timestamp": datetime.utcnow().isoformat(),
            "summary": f"{healthy_count}/{total_count} services healthy",
            "services": results
        }
        
    except Exception as e:
        logger.error(f"💥 Erro na validação forçada: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Erro interno na validação de serviços",
                "error": str(e)
            }
        )

@router.get("/health/circuit-breakers")
async def get_circuit_breakers_status():
    """
    Get status of all circuit breakers.
    
    Returns current state and statistics for all circuit breakers.
    """
    try:
        logger.debug("🔍 Status dos circuit breakers solicitado")
        
        circuit_breakers_status = external_service_validator.get_circuit_breaker_status()
        
        # Adicionar estatísticas
        stats = {
            "total_breakers": len(circuit_breakers_status),
            "open_breakers": sum(1 for cb in circuit_breakers_status.values() if cb["state"] == "open"),
            "half_open_breakers": sum(1 for cb in circuit_breakers_status.values() if cb["state"] == "half_open"),
            "closed_breakers": sum(1 for cb in circuit_breakers_status.values() if cb["state"] == "closed")
        }
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "statistics": stats,
            "circuit_breakers": circuit_breakers_status
        }
        
    except Exception as e:
        logger.error(f"💥 Erro ao obter status dos circuit breakers: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Erro interno ao obter status dos circuit breakers",
                "error": str(e)
            }
        )

def _format_uptime(seconds: float) -> str:
    """Format uptime in human readable format."""
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    
    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"