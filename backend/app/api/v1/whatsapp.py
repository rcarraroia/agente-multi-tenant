from fastapi import APIRouter, Depends, HTTPException, status
from app.services.tenant_service import TenantService
from app.services.whatsapp.providers.evolution import EvolutionProvider
from app.schemas.tenant import TenantUpdate, Tenant
from app.services.whatsapp.models import InstanceConfig, ConnectionStatus
import os

from app.api.deps import get_current_tenant

router = APIRouter()

def get_whatsapp_provider():
    # TODO: Refactor to a common dependencies file
    api_url = os.getenv("EVOLUTION_API_URL")
    api_key = os.getenv("EVOLUTION_API_KEY")
    if not api_url or not api_key:
        raise HTTPException(status_code=500, detail="Evolution API not configured")
    return EvolutionProvider(api_url=api_url, api_key=api_key)

@router.post("/connect")
async def connect_whatsapp(
    tenant: Tenant = Depends(get_current_tenant),
    provider: EvolutionProvider = Depends(get_whatsapp_provider),
    tenant_service: TenantService = Depends()
):
    # 1. Tenant is already retrieved and subscription validated by Dependency Injection

    if tenant.evolution_instance_id:
        # Check status
        status = await provider.get_connection_status(tenant.evolution_instance_id)
        if status == ConnectionStatus.CONNECTED:
             raise HTTPException(status_code=400, detail="Already connected")
        # If not connected, we might want to recreate or just get QR
        # For simplicity, if instance exists, we return success and let user call /qrcode
        
    # 2. Create Instance
    instance_name = f"tenant_{tenant.id}"
    config = InstanceConfig(
        instance_name=instance_name,
        tenant_id=str(tenant.id),
        settings={"chatwoot": {
            "account_id": tenant.chatwoot_account_id or 1, # Default or from tenant
            "url": os.getenv("CHATWOOT_URL"),
            "token": os.getenv("CHATWOOT_ADMIN_TOKEN") # Should be admin token to create inbox
        }}
    )
    
    try:
        data = await provider.create_instance(config)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Provider error: {str(e)}")

    # 3. Update Tenant
    update_data = TenantUpdate(
        evolution_instance_id=instance_name,
        whatsapp_provider="evolution",
        whatsapp_status="waiting_qr"
    )
    tenant_service.update_tenant(tenant.id, update_data)

    return {"status": "created", "instance_name": instance_name}

@router.get("/status")
async def get_status(
    tenant: Tenant = Depends(get_current_tenant),
    provider: EvolutionProvider = Depends(get_whatsapp_provider),
):
    if not tenant.evolution_instance_id:
        return {"status": "disconnected"}

    status = await provider.get_connection_status(tenant.evolution_instance_id)
    
    # Sync with DB if needed
    # tenant_service.update_tenant(tenant.id, TenantUpdate(whatsapp_status=status.value))
    
    return {"status": status}

@router.get("/qrcode")
async def get_qrcode(
    tenant: Tenant = Depends(get_current_tenant),
    provider: EvolutionProvider = Depends(get_whatsapp_provider),
):
    if not tenant.evolution_instance_id:
        raise HTTPException(status_code=400, detail="Instance not created. Call /connect first.")
        
    qr_data = await provider.get_qr_code(tenant.evolution_instance_id)
    
    if not qr_data:
        return {"qrcode": None, "message": "No QR Code available (maybe connected?)"}
        
    return {"qrcode": qr_data.code, "type": qr_data.type}

@router.post("/disconnect")
async def disconnect_whatsapp(
    tenant: Tenant = Depends(get_current_tenant),
    provider: EvolutionProvider = Depends(get_whatsapp_provider),
    tenant_service: TenantService = Depends()
):
    if not tenant.evolution_instance_id:
        raise HTTPException(status_code=400, detail="No instance to disconnect")
        
    try:
        # 1. Logout/Delete instance from Evolution
        await provider.delete_instance(tenant.evolution_instance_id)
        
        # 2. Update Tenant in DB
        update_data = TenantUpdate(
            evolution_instance_id=None,
            whatsapp_status="disconnected"
        )
        tenant_service.update_tenant(tenant.id, update_data)
        
        return {"status": "success", "message": "Disconnected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error disconnecting: {str(e)}")
