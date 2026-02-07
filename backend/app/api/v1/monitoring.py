"""
Monitoring and Performance Dashboard API.

Endpoints para monitoramento de performance, métricas do sistema
e dashboard básico de observabilidade.
"""

from fastapi import APIRouter, HTTPException, status, Query, Depends
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
import asyncio

from app.core.logging import get_structured_logger, PerformanceLogger, AuditLogger
from app.services.external_service_validator import external_service_validator
from app.services.consistency_monitor import ConsistencyMonitor
from app.config import settings
from app.api.deps import get_current_user_id

logger = get_structured_logger(__name__)
router = APIRouter()

# Instância do monitor de consistência
consistency_monitor = ConsistencyMonitor()

class PerformanceMetrics(BaseModel):
    """Métricas de performance do sistema."""
    timestamp: datetime
    request_metrics: Dict[str, Any]
    database_metrics: Dict[str, Any]
    external_services_metrics: Dict[str, Any]
    system_health: Dict[str, Any]

class SystemMetrics(BaseModel):
    """Métricas gerais do sistema."""
    uptime_seconds: float
    total_requests: int
    avg_response_time_ms: float
    error_rate_percent: float
    active_connections: int
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None

class ServiceMetrics(BaseModel):
    """Métricas de um serviço específico."""
    service_name: str
    total_calls: int
    success_rate_percent: float
    avg_response_time_ms: float
    last_error: Optional[str] = None
    circuit_breaker_state: str

# Armazenamento em memória para métricas (em produção, usar Redis)
_metrics_store = {
    "requests": [],
    "database_queries": [],
    "external_calls": [],
    "errors": []
}

# Startup time para cálculo de uptime
startup_time = datetime.utcnow()

@router.get("/metrics", response_model=PerformanceMetrics)
async def get_performance_metrics():
    """
    Obtém métricas de performance do sistema.
    
    Retorna métricas agregadas de:
    - Requests HTTP
    - Queries de banco de dados
    - Chamadas para serviços externos
    - Saúde geral do sistema
    """
    try:
        logger.info("Coletando métricas de performance")
        
        # Calcular métricas de requests
        request_metrics = _calculate_request_metrics()
        
        # Calcular métricas de banco
        database_metrics = _calculate_database_metrics()
        
        # Calcular métricas de serviços externos
        external_metrics = await _calculate_external_services_metrics()
        
        # Calcular saúde do sistema
        system_health = await _calculate_system_health()
        
        metrics = PerformanceMetrics(
            timestamp=datetime.utcnow(),
            request_metrics=request_metrics,
            database_metrics=database_metrics,
            external_services_metrics=external_metrics,
            system_health=system_health
        )
        
        logger.info("Métricas coletadas com sucesso")
        return metrics
        
    except Exception as e:
        logger.error("Erro ao coletar métricas", exception=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Erro interno ao coletar métricas",
                "error": str(e)
            }
        )

@router.get("/metrics/system", response_model=SystemMetrics)
async def get_system_metrics():
    """
    Obtém métricas básicas do sistema.
    
    Inclui uptime, contadores gerais e estatísticas básicas.
    """
    try:
        uptime = (datetime.utcnow() - startup_time).total_seconds()
        
        # Calcular métricas básicas
        total_requests = len(_metrics_store["requests"])
        
        # Calcular tempo médio de resposta (últimas 100 requests)
        recent_requests = _metrics_store["requests"][-100:]
        avg_response_time = 0
        if recent_requests:
            avg_response_time = sum(r.get("duration_ms", 0) for r in recent_requests) / len(recent_requests)
        
        # Calcular taxa de erro (últimas 100 requests)
        error_rate = 0
        if recent_requests:
            errors = sum(1 for r in recent_requests if r.get("status_code", 200) >= 400)
            error_rate = (errors / len(recent_requests)) * 100
        
        metrics = SystemMetrics(
            uptime_seconds=uptime,
            total_requests=total_requests,
            avg_response_time_ms=round(avg_response_time, 2),
            error_rate_percent=round(error_rate, 2),
            active_connections=1  # Placeholder - em produção, obter do servidor
        )
        
        return metrics
        
    except Exception as e:
        logger.error("Erro ao coletar métricas do sistema", exception=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Erro interno ao coletar métricas do sistema",
                "error": str(e)
            }
        )

@router.get("/metrics/services", response_model=List[ServiceMetrics])
async def get_services_metrics():
    """
    Obtém métricas de todos os serviços externos.
    
    Inclui estatísticas de chamadas, taxa de sucesso e estado dos circuit breakers.
    """
    try:
        logger.info("Coletando métricas de serviços externos")
        
        # Obter status dos circuit breakers
        circuit_breakers = external_service_validator.get_circuit_breaker_status()
        
        # Calcular métricas para cada serviço
        services_metrics = []
        
        for service_name, cb_status in circuit_breakers.items():
            # Filtrar chamadas deste serviço
            service_calls = [
                call for call in _metrics_store["external_calls"]
                if call.get("service") == service_name
            ]
            
            total_calls = len(service_calls)
            success_calls = sum(1 for call in service_calls if call.get("success", False))
            success_rate = (success_calls / total_calls * 100) if total_calls > 0 else 0
            
            avg_response_time = 0
            if service_calls:
                avg_response_time = sum(call.get("duration_ms", 0) for call in service_calls) / len(service_calls)
            
            # Último erro
            last_error = None
            error_calls = [call for call in service_calls if not call.get("success", False)]
            if error_calls:
                last_error = error_calls[-1].get("error", "Unknown error")
            
            metrics = ServiceMetrics(
                service_name=service_name,
                total_calls=total_calls,
                success_rate_percent=round(success_rate, 2),
                avg_response_time_ms=round(avg_response_time, 2),
                last_error=last_error,
                circuit_breaker_state=cb_status["state"]
            )
            
            services_metrics.append(metrics)
        
        logger.info(f"Métricas coletadas para {len(services_metrics)} serviços")
        return services_metrics
        
    except Exception as e:
        logger.error("Erro ao coletar métricas de serviços", exception=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Erro interno ao coletar métricas de serviços",
                "error": str(e)
            }
        )

@router.get("/dashboard")
async def get_dashboard_data():
    """
    Obtém dados completos para dashboard de monitoramento.
    
    Combina todas as métricas em uma resposta única para facilitar
    a construção de dashboards frontend.
    """
    try:
        logger.info("Gerando dados do dashboard")
        
        # Coletar todas as métricas em paralelo
        system_metrics, services_metrics, performance_metrics = await asyncio.gather(
            get_system_metrics(),
            get_services_metrics(),
            get_performance_metrics()
        )
        
        # Calcular estatísticas adicionais
        dashboard_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "system": system_metrics.dict(),
            "services": [service.dict() for service in services_metrics],
            "performance": performance_metrics.dict(),
            "alerts": _generate_alerts(system_metrics, services_metrics),
            "summary": {
                "overall_health": _calculate_overall_health(system_metrics, services_metrics),
                "critical_issues": _count_critical_issues(services_metrics),
                "uptime_human": _format_uptime(system_metrics.uptime_seconds)
            }
        }
        
        logger.info("Dashboard gerado com sucesso")
        return dashboard_data
        
    except Exception as e:
        logger.error("Erro ao gerar dashboard", exception=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Erro interno ao gerar dashboard",
                "error": str(e)
            }
        )

@router.post("/metrics/record")
async def record_metric(metric_type: str, data: Dict[str, Any]):
    """
    Registra uma métrica personalizada.
    
    Endpoint interno para registrar métricas de outros componentes.
    """
    try:
        if metric_type not in _metrics_store:
            _metrics_store[metric_type] = []
        
        # Adicionar timestamp
        data["timestamp"] = datetime.utcnow().isoformat()
        
        # Limitar tamanho do store (manter apenas últimos 1000 registros)
        _metrics_store[metric_type].append(data)
        if len(_metrics_store[metric_type]) > 1000:
            _metrics_store[metric_type] = _metrics_store[metric_type][-1000:]
        
        return {"message": "Métrica registrada com sucesso"}
        
    except Exception as e:
        logger.error("Erro ao registrar métrica", exception=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Erro interno ao registrar métrica",
                "error": str(e)
            }
        )

# ============================================
# FUNÇÕES AUXILIARES
# ============================================

def _calculate_request_metrics() -> Dict[str, Any]:
    """Calcula métricas de requests HTTP."""
    requests = _metrics_store["requests"]
    
    if not requests:
        return {
            "total_requests": 0,
            "avg_response_time_ms": 0,
            "requests_per_minute": 0,
            "status_codes": {}
        }
    
    # Últimos 60 minutos
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    recent_requests = [
        r for r in requests 
        if datetime.fromisoformat(r.get("timestamp", "1970-01-01")) > one_hour_ago
    ]
    
    # Calcular métricas
    total = len(requests)
    recent_total = len(recent_requests)
    
    avg_response_time = 0
    if requests:
        avg_response_time = sum(r.get("duration_ms", 0) for r in requests) / len(requests)
    
    requests_per_minute = recent_total / 60 if recent_total > 0 else 0
    
    # Contar status codes
    status_codes = {}
    for request in recent_requests:
        code = request.get("status_code", 200)
        status_codes[str(code)] = status_codes.get(str(code), 0) + 1
    
    return {
        "total_requests": total,
        "recent_requests": recent_total,
        "avg_response_time_ms": round(avg_response_time, 2),
        "requests_per_minute": round(requests_per_minute, 2),
        "status_codes": status_codes
    }

def _calculate_database_metrics() -> Dict[str, Any]:
    """Calcula métricas de banco de dados."""
    queries = _metrics_store["database_queries"]
    
    if not queries:
        return {
            "total_queries": 0,
            "avg_query_time_ms": 0,
            "slow_queries": 0,
            "query_types": {}
        }
    
    total = len(queries)
    avg_time = sum(q.get("duration_ms", 0) for q in queries) / total
    slow_queries = sum(1 for q in queries if q.get("duration_ms", 0) > 1000)  # > 1s
    
    # Contar tipos de query
    query_types = {}
    for query in queries:
        qtype = query.get("query_type", "unknown")
        query_types[qtype] = query_types.get(qtype, 0) + 1
    
    return {
        "total_queries": total,
        "avg_query_time_ms": round(avg_time, 2),
        "slow_queries": slow_queries,
        "query_types": query_types
    }

async def _calculate_external_services_metrics() -> Dict[str, Any]:
    """Calcula métricas de serviços externos."""
    calls = _metrics_store["external_calls"]
    
    if not calls:
        return {
            "total_calls": 0,
            "success_rate": 100,
            "avg_response_time_ms": 0,
            "services_status": {}
        }
    
    total = len(calls)
    successful = sum(1 for call in calls if call.get("success", False))
    success_rate = (successful / total * 100) if total > 0 else 100
    
    avg_time = sum(call.get("duration_ms", 0) for call in calls) / total
    
    # Status dos serviços
    services_status = {}
    for call in calls:
        service = call.get("service", "unknown")
        if service not in services_status:
            services_status[service] = {"calls": 0, "successes": 0}
        
        services_status[service]["calls"] += 1
        if call.get("success", False):
            services_status[service]["successes"] += 1
    
    return {
        "total_calls": total,
        "success_rate": round(success_rate, 2),
        "avg_response_time_ms": round(avg_time, 2),
        "services_status": services_status
    }

async def _calculate_system_health() -> Dict[str, Any]:
    """Calcula saúde geral do sistema."""
    try:
        # Obter status dos serviços externos
        services_status = external_service_validator.get_service_status_summary()
        
        # Calcular score de saúde (0-100)
        health_score = 100
        
        # Penalizar por serviços indisponíveis
        if services_status["overall_status"] == "unhealthy":
            health_score -= 50
        elif services_status["overall_status"] == "degraded":
            health_score -= 25
        
        # Penalizar por alta taxa de erro
        requests = _metrics_store["requests"][-100:]  # Últimos 100 requests
        if requests:
            errors = sum(1 for r in requests if r.get("status_code", 200) >= 400)
            error_rate = errors / len(requests)
            health_score -= int(error_rate * 30)  # Máximo -30 pontos
        
        health_score = max(0, health_score)
        
        return {
            "health_score": health_score,
            "status": "healthy" if health_score >= 80 else "degraded" if health_score >= 50 else "unhealthy",
            "services_summary": services_status["summary"],
            "last_check": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "health_score": 0,
            "status": "unknown",
            "error": str(e),
            "last_check": datetime.utcnow().isoformat()
        }

def _generate_alerts(system_metrics: SystemMetrics, services_metrics: List[ServiceMetrics]) -> List[Dict[str, Any]]:
    """Gera alertas baseados nas métricas."""
    alerts = []
    
    # Alerta de alta taxa de erro
    if system_metrics.error_rate_percent > 10:
        alerts.append({
            "type": "error_rate",
            "severity": "high" if system_metrics.error_rate_percent > 25 else "medium",
            "message": f"Taxa de erro alta: {system_metrics.error_rate_percent}%",
            "timestamp": datetime.utcnow().isoformat()
        })
    
    # Alerta de tempo de resposta alto
    if system_metrics.avg_response_time_ms > 2000:
        alerts.append({
            "type": "response_time",
            "severity": "high" if system_metrics.avg_response_time_ms > 5000 else "medium",
            "message": f"Tempo de resposta alto: {system_metrics.avg_response_time_ms}ms",
            "timestamp": datetime.utcnow().isoformat()
        })
    
    # Alertas de serviços
    for service in services_metrics:
        if service.circuit_breaker_state == "open":
            alerts.append({
                "type": "circuit_breaker",
                "severity": "high",
                "message": f"Circuit breaker aberto para {service.service_name}",
                "timestamp": datetime.utcnow().isoformat()
            })
        
        if service.success_rate_percent < 90:
            alerts.append({
                "type": "service_degraded",
                "severity": "medium",
                "message": f"Taxa de sucesso baixa para {service.service_name}: {service.success_rate_percent}%",
                "timestamp": datetime.utcnow().isoformat()
            })
    
    return alerts

def _calculate_overall_health(system_metrics: SystemMetrics, services_metrics: List[ServiceMetrics]) -> str:
    """Calcula saúde geral do sistema."""
    if system_metrics.error_rate_percent > 25:
        return "unhealthy"
    
    unhealthy_services = sum(1 for s in services_metrics if s.circuit_breaker_state == "open")
    if unhealthy_services > 0:
        return "degraded"
    
    if system_metrics.error_rate_percent > 10 or system_metrics.avg_response_time_ms > 2000:
        return "degraded"
    
    return "healthy"

def _count_critical_issues(services_metrics: List[ServiceMetrics]) -> int:
    """Conta issues críticos."""
    critical = 0
    
    for service in services_metrics:
        if service.circuit_breaker_state == "open":
            critical += 1
        if service.success_rate_percent < 50:
            critical += 1
    
    return critical

def _format_uptime(seconds: float) -> str:
    """Formata uptime em formato legível."""
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    
    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"

# ============================================
# FUNÇÕES PARA REGISTRAR MÉTRICAS
# ============================================

def record_request_metric(method: str, path: str, duration_ms: float, status_code: int, user_id: str = None):
    """Registra métrica de request HTTP."""
    _metrics_store["requests"].append({
        "method": method,
        "path": path,
        "duration_ms": duration_ms,
        "status_code": status_code,
        "user_id": user_id,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    # Limitar tamanho
    if len(_metrics_store["requests"]) > 1000:
        _metrics_store["requests"] = _metrics_store["requests"][-1000:]

def record_database_metric(query_type: str, table: str, duration_ms: float, rows_affected: int = None):
    """Registra métrica de query de banco."""
    _metrics_store["database_queries"].append({
        "query_type": query_type,
        "table": table,
        "duration_ms": duration_ms,
        "rows_affected": rows_affected,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    # Limitar tamanho
    if len(_metrics_store["database_queries"]) > 1000:
        _metrics_store["database_queries"] = _metrics_store["database_queries"][-1000:]

def record_external_service_metric(service: str, operation: str, duration_ms: float, success: bool, error: str = None):
    """Registra métrica de chamada para serviço externo."""
    _metrics_store["external_calls"].append({
        "service": service,
        "operation": operation,
        "duration_ms": duration_ms,
        "success": success,
        "error": error,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    # Limitar tamanho
    if len(_metrics_store["external_calls"]) > 1000:
        _metrics_store["external_calls"] = _metrics_store["external_calls"][-1000:]

# ============================================
# ENDPOINTS DE CONSISTÊNCIA DE DADOS
# ============================================

@router.get("/metrics/consistency")
async def get_consistency_metrics():
    """Obtém métricas de consistência de dados."""
    try:
        # Obter status do monitor de consistência
        status = await consistency_monitor.get_monitoring_status()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "data_consistency": status
        }
        
    except Exception as e:
        logger.error("Erro ao obter métricas de consistência", exception=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Erro interno ao obter métricas de consistência",
                "error": str(e)
            }
        )

@router.post("/consistency/check")
async def trigger_consistency_check():
    """Dispara uma verificação manual de consistência."""
    try:
        logger.info("Verificação manual de consistência solicitada")
        
        # Executar verificação
        result = await consistency_monitor.run_consistency_check()
        
        return {
            "message": "Verificação de consistência concluída",
            "timestamp": datetime.utcnow().isoformat(),
            "result": {
                "is_consistent": result.is_consistent,
                "total_checked": result.total_checked,
                "inconsistencies_found": result.inconsistencies_found,
                "missing_in_services": len(result.missing_in_services),
                "missing_in_subscriptions": len(result.missing_in_subscriptions),
                "status_mismatches": len(result.status_mismatches),
                "date_conflicts": len(result.date_conflicts)
            }
        }
        
    except Exception as e:
        logger.error("Erro ao disparar verificação de consistência", exception=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Erro interno ao disparar verificação",
                "error": str(e)
            }
        )

@router.post("/consistency/sync")
async def trigger_consistency_sync(
    dry_run: bool = Query(True, description="Executar em modo dry-run (sem alterações)"),
    current_user_id: str = Depends(get_current_user_id)
):
    """Dispara uma sincronização para resolver inconsistências."""
    try:
        logger.info(f"Sincronização de consistência solicitada (dry_run={dry_run})")
        
        # Log de auditoria
        logger.info(
            "consistency_sync_requested",
            user_id=current_user_id,
            dry_run=dry_run
        )
        
        # Executar sincronização
        result = await consistency_monitor.force_sync_inconsistencies(dry_run)
        
        return {
            "message": f"Sincronização {'simulada' if dry_run else 'executada'} com sucesso",
            "timestamp": datetime.utcnow().isoformat(),
            "result": result
        }
        
    except Exception as e:
        logger.error("Erro ao disparar sincronização", exception=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Erro interno ao disparar sincronização",
                "error": str(e)
            }
        )

@router.get("/alerts")
async def get_active_alerts():
    """Obtém alertas ativos do sistema."""
    try:
        # TODO: Implementar sistema de alertas persistente
        # Por enquanto, retornar estrutura básica
        
        alerts = {
            "timestamp": datetime.utcnow().isoformat(),
            "active_alerts": [],
            "alert_summary": {
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0
            },
            "last_24h_count": 0
        }
        
        return alerts
        
    except Exception as e:
        logger.error("Erro ao obter alertas", exception=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Erro interno ao obter alertas",
                "error": str(e)
            }
        )