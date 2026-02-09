from typing import Generator, Optional, Any, Annotated
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import UUID4
from uuid import UUID
from datetime import datetime

from app.config import settings
from app.core import security
from app.core.security import jwt_security_manager
from app.core.tenant_resolver import get_tenant_from_jwt, tenant_resolver
from app.core.logging import log_tenant_resolution, log_subscription_check, set_tenant_context, get_logger
from app.core.exceptions import CredentialsException, EntityNotFoundException, PermissionDeniedException
from app.db.supabase import get_supabase
from app.services.tenant_service import TenantService
from app.services.subscription_synchronizer import SubscriptionSynchronizer
from app.schemas.tenant import Tenant
from app.schemas.common import BaseResponse

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/login/access-token", auto_error=False)

logger = get_logger(__name__)

class APIResponse(BaseResponse):
    data: Optional[Any] = None

def get_current_user_id(token: Annotated[str, Depends(oauth2_scheme)]) -> str:
    """
    Validates JWT and returns the user_id (sub) with enhanced security validation.
    
    ATUALIZADO: Usa JWTSecurityManager para validação avançada de tokens
    com logs de segurança detalhados.
    """
    if not token:
        logger.warning("🚨 Tentativa de acesso sem token")
        raise CredentialsException(
            detail="Token de acesso não fornecido",
            error_code="AUTH_001",
            error_type="missing_token"
        )

    try:
        # Usar JWTSecurityManager para validação avançada
        payload = jwt_security_manager.verify_token(token, token_type="access")
        user_id: str = payload.get("sub")
        
        if user_id is None:
            logger.warning("🚨 Token válido mas sem subject (sub)")
            raise CredentialsException(
                detail="Token inválido: subject não encontrado",
                error_code="AUTH_002", 
                error_type="invalid_subject"
            )
        
        logger.debug(f"✅ Usuário autenticado com sucesso: {user_id}")
        return user_id
        
    except CredentialsException as e:
        # Log de tentativa de acesso negada
        logger.warning(f"🚨 Acesso negado: {e.detail}")
        logger.warning(f"   Código: {getattr(e, 'error_code', 'AUTH_UNKNOWN')}")
        logger.warning(f"   Tipo: {getattr(e, 'error_type', 'unknown')}")
        raise e
        
    except Exception as e:
        # Log de erro inesperado
        logger.error(f"💥 Erro inesperado na autenticação: {str(e)}")
        raise CredentialsException(
            detail="Erro interno na validação do token",
            error_code="AUTH_003",
            error_type="internal_error"
        )

def get_current_affiliate_id(
    user_id: Annotated[str, Depends(get_current_user_id)]
) -> UUID:
    """
    Fetches affiliate_id corresponding to the authenticated user schema.
    
    ATUALIZADO: Melhor tratamento de erros e logs de segurança.
    """
    try:
        supabase = get_supabase()
        
        # Query affiliates table directly to find affiliate by user_id
        response = supabase.table("affiliates")\
            .select("id")\
            .eq("user_id", user_id)\
            .execute()

        if not response.data:
            # User is authenticated but not an affiliate
            logger.warning(f"🚨 Usuário autenticado mas não é afiliado: {user_id}")
            raise PermissionDeniedException(
                detail="Usuário não possui perfil de afiliado",
                error_code="AUTH_004",
                error_type="not_affiliate"
            )
        
        id_value = response.data[0]["id"]
        affiliate_id = id_value if isinstance(id_value, UUID) else UUID(id_value)
        logger.debug(f"✅ Afiliado identificado: {affiliate_id} (user: {user_id})")
        
        return affiliate_id
        
    except PermissionDeniedException:
        raise
    except Exception as e:
        logger.error(f"💥 Erro ao buscar affiliate_id para user {user_id}: {str(e)}")
        raise PermissionDeniedException(
            detail="Erro interno ao validar perfil de afiliado",
            error_code="AUTH_005",
            error_type="database_error"
        )

def check_affiliate_subscription(affiliate_id: UUID) -> bool:
    """
    Checks if the affiliate has an active subscription using unified subscription logic.
    
    ATUALIZADO: Usa SubscriptionSynchronizer para obter visão unificada
    dos dados entre affiliate_services e multi_agent_subscriptions.
    """
    try:
        # Usar SubscriptionSynchronizer para obter dados unificados
        synchronizer = SubscriptionSynchronizer()
        
        # Executar de forma síncrona (FastAPI permite)
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            unified_subscription = loop.run_until_complete(
                synchronizer.get_unified_subscription(affiliate_id)
            )
        finally:
            loop.close()
        
        # Verificar se há assinatura ativa
        has_subscription = False
        if unified_subscription:
            has_subscription = unified_subscription.is_active
            
            # Log adicional para auditoria
            logger.info(f"🔍 Verificação de assinatura unificada para {affiliate_id}")
            logger.info(f"   Status: {unified_subscription.status}")
            logger.info(f"   Ativa: {has_subscription}")
            logger.info(f"   Fonte primária: {unified_subscription.primary_source}")
            logger.info(f"   Conflitos: {len(unified_subscription.conflicts)}")
        else:
            logger.info(f"❌ Nenhuma assinatura encontrada para afiliado {affiliate_id}")
        
        # Log da verificação de assinatura (mantém compatibilidade)
        log_subscription_check(affiliate_id, has_subscription)
        
        return has_subscription
        
    except Exception as e:
        logger.error(f"💥 Erro ao verificar assinatura unificada para {affiliate_id}: {str(e)}")
        
        # Fallback para método antigo em caso de erro
        logger.warning(f"⚠️ Usando fallback para verificação de assinatura do afiliado {affiliate_id}")
        
        supabase = get_supabase()
        response = supabase.table("affiliate_services")\
            .select("status", "expires_at")\
            .eq("affiliate_id", str(affiliate_id))\
            .eq("service_type", "agente_ia")\
            .execute()

        has_subscription = False
        
        if response.data:
            service = response.data[0]
            if service["status"] == "active":
                if service.get("expires_at"):
                    expires_at = datetime.fromisoformat(service["expires_at"].replace("Z", "+00:00"))
                    has_subscription = expires_at >= datetime.now(expires_at.tzinfo)
                else:
                    has_subscription = True
        
        # Log da verificação de assinatura
        log_subscription_check(affiliate_id, has_subscription)
        
        return has_subscription

def get_current_tenant(
    token: Annotated[str, Depends(oauth2_scheme)]
) -> Tenant:
    """
    Resolves the tenant for the current request using JWT-based resolution.
    Also validates if the affiliate has an active subscription using unified logic.
    
    ATUALIZADO: Usa tenant_resolver com logs de auditoria completos,
    SubscriptionSynchronizer para validação unificada de assinatura,
    e tratamento de erros melhorado com códigos específicos.
    """
    if not token:
        logger.warning("🚨 Tentativa de resolução de tenant sem token")
        raise CredentialsException(
            detail="Token de acesso não fornecido para resolução de tenant",
            error_code="TENANT_001",
            error_type="missing_token"
        )
    
    try:
        # 1. Resolver tenant via JWT (inclui validação de affiliate_id)
        tenant = get_tenant_from_jwt(token)
        
        # 2. Configurar contexto de logging
        set_tenant_context(
            tenant_id=UUID(tenant.id),
            affiliate_id=UUID(tenant.affiliate_id),
            user_id=None  # Será definido quando disponível
        )
        
        # 3. Log de resolução bem-sucedida
        log_tenant_resolution(
            user_id="extracted_from_jwt",  # Placeholder
            affiliate_id=UUID(tenant.affiliate_id),
            tenant_id=UUID(tenant.id),
            success=True
        )
        
        # 4. Verificar assinatura ativa usando SubscriptionSynchronizer
        if not check_affiliate_subscription(UUID(tenant.affiliate_id)):
            logger.warning(f"🚨 Assinatura inativa para tenant {tenant.id} (afiliado: {tenant.affiliate_id})")
            raise PermissionDeniedException(
                detail="Assinatura do Agente IA inativa ou expirada",
                error_code="TENANT_002",
                error_type="subscription_inactive"
            )
        
        logger.debug(f"✅ Tenant resolvido com sucesso: {tenant.id}")
        return tenant
        
    except (CredentialsException, EntityNotFoundException, PermissionDeniedException) as e:
        # Log de falha na resolução
        try:
            payload = jwt_security_manager.verify_token(token)
            user_id = payload.get("sub", "unknown")
        except:
            user_id = "invalid_token"
        
        error_code = getattr(e, 'error_code', 'TENANT_UNKNOWN')
        error_type = getattr(e, 'error_type', 'unknown')
        
        log_tenant_resolution(
            user_id=user_id,
            affiliate_id=UUID("00000000-0000-0000-0000-000000000000"),  # Placeholder para erro
            tenant_id=UUID("00000000-0000-0000-0000-000000000000"),  # Placeholder para erro
            success=False,
            error=f"{error_code}: {str(e)}"
        )
        
        logger.warning(f"🚨 Falha na resolução de tenant: {str(e)}")
        logger.warning(f"   Código: {error_code}")
        logger.warning(f"   Tipo: {error_type}")
        
        raise
        
    except Exception as e:
        logger.error(f"💥 Erro inesperado na resolução de tenant: {str(e)}")
        raise CredentialsException(
            detail="Erro interno ao resolver tenant",
            error_code="TENANT_003",
            error_type="internal_error"
        )

def get_tenant_context(request: Request) -> Tenant:
    """
    Função utilitária para resolver tenant a partir de Request.
    Útil para endpoints que precisam de tenant mas não usam Depends.
    
    ATUALIZADO: Usa tenant_resolver com logs de auditoria.
    """
    try:
        tenant = tenant_resolver.get_tenant_from_request(request)
        
        # Configurar contexto de logging
        set_tenant_context(
            tenant_id=UUID(tenant.id),
            affiliate_id=UUID(tenant.affiliate_id)
        )
        
        return tenant
    except Exception as e:
        # Log de erro
        log_tenant_resolution(
            user_id="from_request",
            affiliate_id=UUID("00000000-0000-0000-0000-000000000000"),
            tenant_id=UUID("00000000-0000-0000-0000-000000000000"),
            success=False,
            error=str(e)
        )
        raise
