from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config import settings
from app.db.supabase import get_supabase
from app.core.logging import setup_logging, get_logger
from app.core.config_manager import config_manager
from app.services.external_service_validator import external_service_validator
from app.middleware.logging_middleware import LoggingMiddleware, AuditMiddleware

# Configurar logging no início
setup_logging()
logger = get_logger('main')

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize resources
    try:
        logger.info("🚀 Iniciando aplicação Agente Multi-Tenant")
        
        # Validar configuração
        logger.info("🔍 Validando configuração do sistema...")
        is_valid, errors, warnings = config_manager.validate_all(strict=False)
        
        if not is_valid:
            logger.error(f"❌ Configuração inválida: {len(errors)} erros encontrados")
            for error in errors:
                logger.error(f"  - {error}")
            # Em produção, podemos querer falhar aqui
            if settings.ENVIRONMENT == "production":
                raise Exception("Configuração inválida para produção")
        
        if warnings:
            logger.warning(f"⚠️ Avisos de configuração: {len(warnings)}")
            for warning in warnings:
                logger.warning(f"  - {warning}")
        
        # Log resumo da configuração
        config_manager.log_configuration_summary()
        
        # Check DB connection
        client = get_supabase()
        logger.info("✅ Conexão com Supabase estabelecida")
        
        # Validar serviços externos no startup
        logger.info("🔍 Validando conectividade com serviços externos...")
        try:
            services_health = await external_service_validator.validate_all_services()
            
            healthy_count = sum(1 for check in services_health.values() if check.status == "healthy")
            total_count = len(services_health)
            
            logger.info(f"📊 Validação de serviços externos concluída: {healthy_count}/{total_count} saudáveis")
            
            # Log detalhes dos serviços
            for service_name, check in services_health.items():
                if check.status == "healthy":
                    logger.info(f"  ✅ {service_name}: {check.status} ({check.response_time_ms:.0f}ms)")
                elif check.status == "degraded":
                    logger.warning(f"  ⚠️ {service_name}: {check.status} - {check.error_message}")
                else:
                    logger.warning(f"  ❌ {service_name}: {check.status} - {check.error_message}")
            
            # Em produção, avisar sobre serviços críticos indisponíveis
            if settings.ENVIRONMENT == "production":
                critical_services = ["evolution_api", "chatwoot"]
                unhealthy_critical = [
                    name for name in critical_services 
                    if name in services_health and services_health[name].status == "unhealthy"
                ]
                
                if unhealthy_critical:
                    logger.error(f"🚨 Serviços críticos indisponíveis em produção: {unhealthy_critical}")
                    logger.error("   Sistema pode ter funcionalidade limitada")
                
        except Exception as e:
            logger.error(f"💥 Erro na validação de serviços externos: {str(e)}")
            logger.warning("⚠️ Continuando inicialização sem validação de serviços externos")
        
    except Exception as e:
        logger.error(f"💥 Erro no startup: {e}")
        raise
    
    yield
    
    # Shutdown: Clean up resources
    logger.info("🔄 Finalizando aplicação Agente Multi-Tenant")

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Adicionar middlewares de logging ANTES dos outros middlewares
app.add_middleware(AuditMiddleware)
app.add_middleware(LoggingMiddleware)

from app.api.v1.router import api_router
app.include_router(api_router, prefix=settings.API_V1_STR)

# CORS Configuration - Configuração simplificada e robusta
cors_origins = settings.cors_origins_list

logger.info(f"🌐 Configurando CORS para ambiente: {settings.ENVIRONMENT}")
logger.info(f"   Origens configuradas: {len(cors_origins)}")

if cors_origins:
    logger.info(f"   Origens permitidas: {cors_origins}")
    
    # Configuração CORS simplificada e robusta
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["*"],
        expose_headers=["X-Total-Count", "X-Request-ID"],
        max_age=600,  # 10 minutos de cache para preflight
    )
    
    logger.info("✅ CORS configurado com sucesso")
    
else:
    # Fallback para desenvolvimento
    logger.warning("⚠️ CORS_ORIGINS não configurado - usando modo permissivo")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

@app.get("/")
def root():
    """Root endpoint com informações básicas."""
    logger.debug("Root endpoint acessado")
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "api_docs": f"{settings.API_V1_STR}/docs",
        "health_check": f"{settings.API_V1_STR}/health"
    }
