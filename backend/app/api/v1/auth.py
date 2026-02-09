"""
Authentication endpoints with enhanced JWT security.

Provides endpoints for:
- Token refresh
- Token validation
- Security information
"""

from fastapi import APIRouter, HTTPException, status, Request
from pydantic import BaseModel
from typing import Dict, Any

# Importações básicas primeiro
router = APIRouter()



# Tentar importações mais complexas depois
try:
    from app.core.security import jwt_security_manager
    from app.core.exceptions import CredentialsException
    from app.core.logging import get_logger
    from app.api.deps import get_current_tenant, get_current_user_id
    from app.schemas.tenant import Tenant
    
    logger = get_logger(__name__)
    IMPORTS_OK = True
except Exception as e:
    logger = None
    IMPORTS_OK = False
    IMPORT_ERROR = str(e)

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

@router.get("/debug/simple-test")
async def simple_debug_test():
    """
    ENDPOINT SIMPLES PARA TESTAR SE AUTH ROUTER FUNCIONA
    """
    return {
        "status": "success",
        "message": "Auth router funcionando",
        "timestamp": "2025-02-08"
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