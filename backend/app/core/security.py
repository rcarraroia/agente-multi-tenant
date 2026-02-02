from datetime import datetime, timedelta
from typing import Any, Union, Optional
from jose import jwt, JWTError
from app.config import settings
from app.core.exceptions import CredentialsException

def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"sub": str(subject), "exp": expire}
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> dict:
    """
    Verifies the JWT token and returns the payload.
    Supports both Supabase Auth tokens and local JWT tokens.
    Raises CredentialsException if invalid.
    """
    try:
        # Primeiro, tenta validar como token Supabase Auth (com audience)
        if settings.SUPABASE_JWT_SECRET:
            try:
                payload = jwt.decode(
                    token,
                    settings.SUPABASE_JWT_SECRET,
                    algorithms=["HS256"],
                    audience="authenticated"  # Audience padrão do Supabase Auth
                )
                return payload
            except JWTError:
                pass  # Fallback para JWT local
        
        # Fallback: JWT local (para testes ou tokens gerados internamente)
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        raise CredentialsException()

def get_tenant_id_from_token(payload: dict) -> Optional[str]:
    """
    Extracts tenant_id from JWT payload metadata if present.
    Adapt based on actual token structure from Slim Quality auth.
    """
    # Placeholder: Assuming tenant_id might be in app_metadata or user_metadata
    # This needs verification with the actual auth implementation
    return payload.get("app_metadata", {}).get("tenant_id")
