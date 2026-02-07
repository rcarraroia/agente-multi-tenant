from fastapi import FastAPI, Request, Response
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

# CORS Configuration com validação aprimorada
cors_origins = settings.cors_origins_list
is_production = settings.ENVIRONMENT.lower() == "production"

# Middleware customizado para log de CORS rejeitados
class CORSLoggingMiddleware:
    def __init__(self, app, origins):
        self.app = app
        self.allowed_origins = origins
        
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            request = Request(scope, receive)
            origin = request.headers.get("origin")
            
            # Log tentativas de CORS
            if origin:
                if self.allowed_origins == ["*"] or origin in self.allowed_origins:
                    logger.debug(f"✅ CORS permitido para origem: {origin}")
                else:
                    logger.warning(f"❌ CORS rejeitado para origem: {origin}")
                    logger.warning(f"   Origens permitidas: {self.allowed_origins}")
        
        await self.app(scope, receive, send)

if cors_origins and cors_origins != ["*"]:
    logger.info(f"🌐 CORS configurado para {len(cors_origins)} origens específicas")
    logger.debug(f"   Origens permitidas: {cors_origins}")
    
    # Configuração restritiva para produção
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=[
            "Accept",
            "Accept-Language",
            "Content-Language",
            "Content-Type",
            "Authorization",
            "X-Requested-With",
            "X-Tenant-ID",
            "X-Affiliate-ID",
            "X-Agent-Name",
            "X-Request-Source"
        ],
        expose_headers=["X-Total-Count", "X-Request-ID"],
        max_age=600,  # 10 minutos de cache para preflight
    )
    
    # Adicionar middleware de logging
    app.add_middleware(CORSLoggingMiddleware, origins=cors_origins)
    
elif is_production:
    # Em produção, NUNCA permitir CORS aberto
    logger.error("❌ CORS não configurado adequadamente para produção!")
    logger.error("   Configure CORS_ORIGINS com origens específicas")
    
    # Configuração mínima de segurança
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://slimquality.com.br"],  # Fallback seguro
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )
    
    logger.warning("⚠️ Usando configuração CORS de fallback para produção")
    
else:
    # Desenvolvimento: CORS permissivo com logs
    logger.warning("⚠️ CORS configurado em modo permissivo (desenvolvimento)")
    logger.warning("   Todas as origens são permitidas - NÃO usar em produção!")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

@app.get("/health")
def health_check():
    """
    Health check endpoint com informações de configuração.
    Não expõe secrets, apenas status geral.
    """
    logger.debug("Health check solicitado")
    
    config_summary = config_manager.get_configuration_summary()
    
    return {
        "status": "ok",
        "environment": settings.ENVIRONMENT,
        "version": "1.0.0",
        "configuration": {
            "database_connected": config_summary["has_supabase_config"],
            "ai_enabled": config_summary["has_openai_config"],
            "whatsapp_enabled": config_summary["has_evolution_config"],
            "chat_enabled": config_summary["has_chatwoot_config"],
            "cors_origins_count": config_summary["cors_origins_count"],
            "is_production": config_summary["is_production"]
        }
    }

@app.get("/")
def root():
    """Root endpoint com informações básicas."""
    logger.debug("Root endpoint acessado")
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "api_docs": f"{settings.API_V1_STR}/docs"
    }
