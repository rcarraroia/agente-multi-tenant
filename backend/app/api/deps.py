from typing import Generator, Optional, Any, Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import UUID4
from uuid import UUID

from app.config import settings
from app.core import security
from app.core.exceptions import CredentialsException, EntityNotFoundException, PermissionDeniedException
from app.db.supabase import get_supabase
from app.services.tenant_service import TenantService
from app.schemas.tenant import Tenant
from app.schemas.common import BaseResponse

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/login/access-token", auto_error=False)

class APIResponse(BaseResponse):
    data: Optional[Any] = None

def get_current_user_id(token: Annotated[str, Depends(oauth2_scheme)]) -> str:
    """
    Validates JWT and returns the user_id (sub).
    """
    if not token:
        # Allow open access for development if DEBUG is True and no token PROVIDED? 
        # No, strict auth unless explicitly bypassed via specific overrides.
        # However, for endpoints that need auth, this will raise.
        raise CredentialsException(detail="Token not provided")

    try:
        payload = security.verify_token(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise CredentialsException(detail="Could not validate credentials")
        return user_id
    except CredentialsException as e:
        raise e
    except Exception as e:
        raise CredentialsException(detail=f"Invalid token: {str(e)}")

def get_current_affiliate_id(
    user_id: Annotated[str, Depends(get_current_user_id)]
) -> UUID:
    """
    Fetches affiliate_id corresponding to the authenticated user schema.
    """
    supabase = get_supabase()
    
    # Query affiliates table directly to find affiliate by user_id
    response = supabase.table("affiliates")\
        .select("id")\
        .eq("user_id", user_id)\
        .execute()

    if not response.data:
        # User is authenticated but not an affiliate
        raise PermissionDeniedException(detail="User is not an affiliate")
    
    return UUID(response.data[0]["id"])

def check_affiliate_subscription(affiliate_id: UUID) -> bool:
    """
    Checks if the affiliate has an active 'agente_ia' service in affiliate_services table.
    """
    supabase = get_supabase()
    response = supabase.table("affiliate_services")\
        .select("status", "expires_at")\
        .eq("affiliate_id", str(affiliate_id))\
        .eq("service_type", "agente_ia")\
        .execute()

    if not response.data:
        return False
    
    service = response.data[0]
    if service["status"] != "active":
        return False
        
    if service.get("expires_at"):
        expires_at = datetime.fromisoformat(service["expires_at"].replace("Z", "+00:00"))
        if expires_at < datetime.now(expires_at.tzinfo):
            return False
            
    return True

def get_current_tenant(
    affiliate_id: Annotated[UUID, Depends(get_current_affiliate_id)]
) -> Tenant:
    """
    Resolves the tenant for the current affiliate. 
    Also validates if the affiliate has an active subscription.
    """
    # 1. Check Subscription First
    if not check_affiliate_subscription(affiliate_id):
        raise PermissionDeniedException(detail="Assinatura do Agente IA inativa ou expirada")

    # 2. Resolve Tenant
    tenant_service = TenantService()
    try:
        tenant = tenant_service.get_by_affiliate_id(affiliate_id)
        if tenant.status == "canceled":
             raise PermissionDeniedException(detail="Tenant is canceled")
        return tenant
    except EntityNotFoundException:
        raise EntityNotFoundException(detail="Tenant not configured for this affiliate")
