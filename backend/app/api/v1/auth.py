"""
Authentication endpoints with enhanced JWT security.

Provides endpoints for:
- Token refresh
- Token validation
- Security information
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from typing import Dict, Any

from app.core.security import jwt_security_manager
from app.core.exceptions import CredentialsException
from app.core.logging import get_logger

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
        
        if len(settings.JWT_SECRET) < 64:
            security_warnings.append("JWT_SECRET tem menos de 64 caracteres")
        
        if settings.JWT_ALGORITHM == "HS256" and len(settings.JWT_SECRET) < 32:
            security_warnings.append("JWT_SECRET muito curto para HS256")
        
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
            "environment_variable": "JWT_SECRET"
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