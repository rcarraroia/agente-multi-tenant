from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import UUID4

from app.api import deps
from app.schemas.tenant import Tenant, TenantCreate, TenantUpdate
from app.services.tenant_service import TenantService
from app.api.deps import APIResponse

router = APIRouter()

@router.post("/", response_model=APIResponse)
def create_tenant(
    *,
    affiliate_id: UUID4 = Depends(deps.get_current_affiliate_id),
    service: TenantService = Depends(TenantService)
) -> Any:
    """
    Create or activate a tenant for the current affiliate.
    Idempotent: if exists, returns existing.
    """
    # Affiliate ID comes from token, ensuring security
    tenant_in = TenantCreate(affiliate_id=affiliate_id)
    try:
        tenant = service.create_tenant(tenant_in)
        return APIResponse(data=tenant)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/me", response_model=APIResponse)
def read_tenant_me(
    tenant: Tenant = Depends(deps.get_current_tenant)
) -> Any:
    """
    Get current tenant details.
    Masks the OpenAI API Key for security.
    """
    tenant_dict = tenant.model_dump()
    if tenant_dict.get("openai_api_key"):
        key = tenant_dict["openai_api_key"]
        if len(key) > 8:
            tenant_dict["openai_api_key"] = f"{key[:4]}{'*' * (len(key) - 8)}{key[-4:]}"
        else:
            tenant_dict["openai_api_key"] = "****"
            
    return APIResponse(data=tenant_dict)

@router.patch("/me", response_model=APIResponse)
def update_tenant_me(
    *,
    tenant_in: TenantUpdate,
    tenant: Tenant = Depends(deps.get_current_tenant),
    service: TenantService = Depends(TenantService)
) -> Any:
    """
    Update current tenant configuration.
    """
    try:
        updated = service.update_tenant(tenant.id, tenant_in)
        return APIResponse(data=updated)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
