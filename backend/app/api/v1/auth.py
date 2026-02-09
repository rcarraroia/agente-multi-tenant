"""
Authentication endpoints with enhanced JWT security.

Provides endpoints for:
- Token refresh
- Token validation
- Security information
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from typing import Dict, Any

from app.core.security import jwt_security_manager
from app.core.exceptions import CredentialsException
from app.core.logging import get_logger
from app.api.deps import get_current_tenant, get_current_user_id
from app.schemas.tenant import Tenant

logger = get_logger(__name__)
router = APIRouter()

# Request/Response Models
class RefreshTokenRequest(BaseModel):
    refresh_token: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenInfoResponse(BaseModel):
    subject: str
    token_type: str
    issued_at: str
    expires_at: str
    is_expired: bool

class SecurityInfoResponse(BaseModel):
    algorithm: str
    secure_configuration: bool
    supported_algorithms: list[str]
    security_warnings: list[str]

@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(request: RefreshTokenRequest):
    """
    Refresh an access token using a valid refresh token.
    
    This endpoint allows clients to obtain a new access token
    without requiring the user to re-authenticate.
    """
    try:
        logger.info("🔄 Solicitação de refresh token recebida")
        
        # Usar JWTSecurityManager para refresh
        tokens = jwt_security_manager.refresh_access_token(request.refresh_token)
        
        logger.info("✅ Tokens renovados com sucesso")
        
        return TokenResponse(**tokens)
        
    except CredentialsException as e:
        logger.warning(f"🚨 Falha no refresh token: {e.detail}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "message": e.detail,
                "error_code": getattr(e, 'error_code', 'REFRESH_FAILED'),
                "error_type": getattr(e, 'error_type', 'refresh_error')
            },
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        logger.error(f"💥 Erro inesperado no refresh: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Erro interno no servidor",
                "error_code": "REFRESH_INTERNAL_ERROR",
                "error_type": "internal_error"
            }
        )

@router.get("/token/info")
async def get_token_info(token: str) -> TokenInfoResponse:
    """
    Get information about a token without validating its signature.
    
    Useful for debugging and token inspection.
    Note: This does not validate the token signature.
    """
    try:
        logger.debug("🔍 Solicitação de informações do token")
        
        token_info = jwt_security_manager.get_token_info(token)
        
        if "error" in token_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Token inválido ou malformado",
                    "error": token_info["error"]
                }
            )
        
        return TokenInfoResponse(
            subject=token_info.get("subject", "unknown"),
            token_type=token_info.get("type", "unknown"),
            issued_at=token_info.get("issued_at_readable", "unknown"),
            expires_at=token_info.get("expires_at_readable", "unknown"),
            is_expired=token_info.get("is_expired", True)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"💥 Erro ao obter informações do token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Erro interno ao processar token",
                "error_code": "TOKEN_INFO_ERROR"
            }
        )

@router.get("/security/info")
async def get_security_info() -> SecurityInfoResponse:
    """
    Get information about the current JWT security configuration.
    
    Useful for security audits and configuration validation.
    """
    try:
        logger.debug("🔍 Solicitação de informações de segurança")
        
        # Obter informações de segurança do JWTSecurityManager
        security_warnings = []
        
        # Verificar se há avisos de configuração
        from app.config import settings
        
        if len(settings.JWT_SECRET_KEY) < 64:
            security_warnings.append("JWT_SECRET_KEY tem menos de 64 caracteres")
        
        if settings.JWT_ALGORITHM == "HS256" and len(settings.JWT_SECRET_KEY) < 32:
            security_warnings.append("JWT_SECRET_KEY muito curto para HS256")
        
        return SecurityInfoResponse(
            algorithm=settings.JWT_ALGORITHM,
            secure_configuration=len(security_warnings) == 0,
            supported_algorithms=jwt_security_manager.SECURE_ALGORITHMS,
            security_warnings=security_warnings
        )
        
    except Exception as e:
        logger.error(f"💥 Erro ao obter informações de segurança: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Erro interno ao obter informações de segurança",
                "error_code": "SECURITY_INFO_ERROR"
            }
        )

@router.post("/security/generate-secret")
async def generate_secure_secret(length: int = 64) -> Dict[str, str]:
    """
    Generate a secure JWT secret.
    
    WARNING: This endpoint should be disabled in production!
    Only use during development or initial setup.
    """
    try:
        from app.config import settings
        
        # Verificar se estamos em produção
        if settings.ENVIRONMENT == "production":
            logger.warning("🚨 Tentativa de gerar secret em produção")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "message": "Geração de secrets desabilitada em produção",
                    "error_code": "PRODUCTION_SECURITY_BLOCK"
                }
            )
        
        if length < 32 or length > 128:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Comprimento deve estar entre 32 e 128 caracteres",
                    "error_code": "INVALID_LENGTH"
                }
            )
        
        logger.warning("⚠️ Gerando novo secret JWT (DESENVOLVIMENTO APENAS)")
        
        secure_secret = jwt_security_manager.generate_secure_secret(length)
        
        return {
            "secret": secure_secret,
            "length": len(secure_secret),
            "warning": "SALVE ESTE SECRET EM LOCAL SEGURO E CONFIGURE NO .env",
            "environment_variable": "JWT_SECRET_KEY"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"💥 Erro ao gerar secret: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Erro interno ao gerar secret",
                "error_code": "SECRET_GENERATION_ERROR"
            }
        )

@router.get("/debug/token")
async def debug_token_validation(request: Request):
    """
    DEBUG ENDPOINT - Testar validação de token
    SEMPRE DISPONÍVEL PARA DEBUG
    """
    try:
        # Extrair token do header
        authorization = request.headers.get("Authorization")
        
        if not authorization:
            return {
                "status": "no_auth_header",
                "error": "No Authorization header",
                "available_headers": list(request.headers.keys()),
                "help": "Adicione header: Authorization: Bearer <seu_token>"
            }
        
        if not authorization.startswith("Bearer "):
            return {
                "status": "invalid_auth_format",
                "error": "Invalid Authorization format",
                "authorization_received": authorization[:50] + "..." if len(authorization) > 50 else authorization,
                "help": "Use formato: Bearer <token>"
            }
        
        token = authorization.replace("Bearer ", "")
        
        # Tentar validar token
        try:
            payload = jwt_security_manager.verify_token(token)
            
            return {
                "status": "success",
                "token_valid": True,
                "payload": payload,
                "user_id": payload.get("sub"),
                "token_type": payload.get("type", "unknown"),
                "audience": payload.get("aud", "unknown"),
                "expires_at": payload.get("exp"),
                "issued_at": payload.get("iat")
            }
            
        except Exception as token_error:
            return {
                "status": "token_validation_failed",
                "token_valid": False,
                "error": str(token_error),
                "error_type": type(token_error).__name__,
                "token_preview": token[:50] + "..." if len(token) > 50 else token,
                "help": "Verifique se o token é válido e não expirou"
            }
        
    except Exception as e:
        return {
            "status": "debug_endpoint_error",
            "error": str(e),
            "error_type": type(e).__name__,
            "help": "Erro interno no endpoint de debug"
        }

@router.get("/debug/generate-test-token")
async def generate_test_token():
    """
    ENDPOINT TEMPORÁRIO - Gerar token de teste com dados reais DA BEATRIZ
    USAR APENAS PARA DEBUG - REMOVER APÓS TESTES
    """
    try:
        # DADOS CORRETOS DA BEATRIZ (usuária com acesso ao painel)
        test_user_id = "71d06370-6757-4d35-a91f-7c2b518bc0af"
        test_email = "bia.aguilar@hotmail.com"
        test_name = "Beatriz Fatima Almeida Carraro"
        
        # Criar token Supabase-like
        from datetime import datetime, timedelta
        import time
        
        # Payload similar ao Supabase Auth
        payload = {
            "aud": "authenticated",
            "exp": int(time.time()) + (24 * 60 * 60),  # 24 horas
            "iat": int(time.time()),
            "iss": "https://vtynmmtuvxreiwcxxlma.supabase.co/auth/v1",
            "sub": test_user_id,
            "email": test_email,
            "phone": "",
            "app_metadata": {
                "provider": "email",
                "providers": ["email"]
            },
            "user_metadata": {
                "email": test_email,
                "email_verified": False,
                "phone_verified": False,
                "sub": test_user_id
            },
            "role": "authenticated",
            "aal": "aal1",
            "amr": [{"method": "password", "timestamp": int(time.time())}],
            "session_id": "beatriz-test-session"
        }
        
        # Gerar token usando SUPABASE_JWT_SECRET
        from app.config import settings
        from jose import jwt
        
        if not settings.SUPABASE_JWT_SECRET:
            return {
                "error": "SUPABASE_JWT_SECRET não configurado",
                "help": "Configure SUPABASE_JWT_SECRET no ambiente"
            }
        
        token = jwt.encode(
            payload,
            settings.SUPABASE_JWT_SECRET,
            algorithm="HS256"
        )
        
        return {
            "status": "success",
            "test_token": token,
            "user_data": {
                "user_id": test_user_id,
                "email": test_email,
                "name": test_name,
                "note": "BEATRIZ - Usuária com acesso ao painel de agentes"
            },
            "usage": {
                "header": f"Authorization: Bearer {token}",
                "test_endpoints": [
                    "/api/v1/auth/debug/token",
                    "/api/v1/auth/debug/tenant", 
                    "/api/v1/whatsapp/status",
                    "/api/v1/whatsapp/connect"
                ]
            },
            "warning": "TOKEN DA BEATRIZ - REMOVER ENDPOINT APÓS DEBUG"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__
        }

@router.get("/debug/tenant")
async def debug_tenant_resolution(request: Request):
    """
    DEBUG ENDPOINT - Testar resolução de tenant
    SEMPRE DISPONÍVEL PARA DEBUG
    """
    try:
        # Extrair token do header
        authorization = request.headers.get("Authorization")
        
        if not authorization:
            return {
                "status": "no_auth_header",
                "error": "No Authorization header for tenant resolution",
                "help": "Adicione header: Authorization: Bearer <seu_token>"
            }
        
        if not authorization.startswith("Bearer "):
            return {
                "status": "invalid_auth_format", 
                "error": "Invalid Authorization format",
                "help": "Use formato: Bearer <token>"
            }
        
        token = authorization.replace("Bearer ", "")
        
        # Tentar resolver tenant manualmente
        try:
            from app.core.tenant_resolver import get_tenant_from_jwt
            tenant = get_tenant_from_jwt(token)
            
            return {
                "status": "success",
                "tenant_resolution": "successful",
                "tenant": {
                    "id": tenant.id,
                    "affiliate_id": tenant.affiliate_id,
                    "status": tenant.status,
                    "agent_name": tenant.agent_name,
                    "whatsapp_status": tenant.whatsapp_status
                }
            }
            
        except Exception as tenant_error:
            # Se falhar, tentar pelo menos validar o token
            try:
                payload = jwt_security_manager.verify_token(token)
                user_id = payload.get("sub")
                
                return {
                    "status": "tenant_resolution_failed",
                    "token_valid": True,
                    "user_id": user_id,
                    "tenant_error": str(tenant_error),
                    "tenant_error_type": type(tenant_error).__name__,
                    "help": "Token válido mas falha na resolução de tenant"
                }
                
            except Exception as token_error:
                return {
                    "status": "token_and_tenant_failed",
                    "token_valid": False,
                    "token_error": str(token_error),
                    "tenant_error": str(tenant_error),
                    "help": "Falha tanto na validação do token quanto na resolução do tenant"
                }
        
    except Exception as e:
        return {
            "status": "debug_endpoint_error",
            "error": str(e),
            "error_type": type(e).__name__,
            "help": "Erro interno no endpoint de debug tenant"
        }
        except Exception as tenant_error:
            # Se falhar, tentar pelo menos validar o token
            try:
                payload = jwt_security_manager.verify_token(token)
                user_id = payload.get("sub")
                
                return {
                    "status": "tenant_resolution_failed",
                    "token_valid": True,
                    "user_id": user_id,
                    "tenant_error": str(tenant_error),
                    "tenant_error_type": type(tenant_error).__name__,
                    "help": "Token válido mas falha na resolução de tenant"
                }
                
            except Exception as token_error:
                return {
                    "status": "token_and_tenant_failed",
                    "token_valid": False,
                    "token_error": str(token_error),
                    "tenant_error": str(tenant_error),
                    "help": "Falha tanto na validação do token quanto na resolução do tenant"
                }
        
    except Exception as e:
        return {
            "status": "debug_endpoint_error",
            "error": str(e),
            "error_type": type(e).__name__,
            "help": "Erro interno no endpoint de debug tenant"
        }