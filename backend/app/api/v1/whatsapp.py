from fastapi import APIRouter, Depends, HTTPException, status
from app.services.tenant_service import TenantService
from app.services.whatsapp.providers.evolution import EvolutionProvider
from app.schemas.tenant import TenantUpdate, Tenant
from app.services.whatsapp.models import InstanceConfig, ConnectionStatus
from app.core.logging import get_logger
import os

from app.api.deps import get_current_tenant

router = APIRouter()
logger = get_logger('whatsapp_operations')

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
    logger.info(
        "Iniciando conexão WhatsApp",
        tenant_id=str(tenant.id),
        user_id=str(tenant.affiliate_id),
        action="whatsapp_connect_start"
    )
    
    # 1. Tenant is already retrieved and subscription validated by Dependency Injection

    if tenant.evolution_instance_id:
        # Check status
        status = await provider.get_connection_status(tenant.evolution_instance_id)
        if status == ConnectionStatus.CONNECTED:
            logger.warning(
                "Tentativa de conexão com instância já conectada",
                tenant_id=str(tenant.id),
                instance_id=tenant.evolution_instance_id,
                action="whatsapp_connect_already_connected"
            )
            raise HTTPException(status_code=400, detail="Already connected")
        # If not connected, we might want to recreate or just get QR
        # For simplicity, if instance exists, we return success and let user call /qrcode
        
    # 2. Create Instance
    instance_name = f"tenant_{tenant.id}"
    
    # Validar chatwoot_account_id obrigatório
    if not tenant.chatwoot_account_id:
        logger.error(
            "Chatwoot account_id não configurado",
            tenant_id=str(tenant.id),
            action="whatsapp_connect_missing_chatwoot"
        )
        raise HTTPException(
            status_code=400,
            detail="Chatwoot account_id não configurado para este tenant"
        )
    
    config = InstanceConfig(
        instance_name=instance_name,
        tenant_id=str(tenant.id),
        settings={"chatwoot": {
            "account_id": tenant.chatwoot_account_id,  # Obrigatório, sem fallback
            "url": os.getenv("CHATWOOT_URL"),
            "token": os.getenv("CHATWOOT_ADMIN_TOKEN") # Should be admin token to create inbox
        }}
    )
    
    try:
        logger.info(
            "Criando instância Evolution API",
            tenant_id=str(tenant.id),
            instance_name=instance_name,
            chatwoot_account_id=tenant.chatwoot_account_id,
            action="whatsapp_create_instance"
        )
        data = await provider.create_instance(config)
        logger.info(
            "Instância Evolution API criada com sucesso",
            tenant_id=str(tenant.id),
            instance_name=instance_name,
            action="whatsapp_create_instance_success"
        )
    except Exception as e:
        logger.error(
            "Erro ao criar instância Evolution API",
            tenant_id=str(tenant.id),
            instance_name=instance_name,
            error=str(e),
            action="whatsapp_create_instance_error"
        )
        raise HTTPException(status_code=500, detail=f"Provider error: {str(e)}")

    # 3. Update Tenant
    update_data = TenantUpdate(
        evolution_instance_id=instance_name,
        whatsapp_provider="evolution",
        whatsapp_status="waiting_qr"
    )
    
    try:
        tenant_service.update_tenant(tenant.id, update_data)
        logger.info(
            "Tenant atualizado com dados da instância",
            tenant_id=str(tenant.id),
            instance_name=instance_name,
            status="waiting_qr",
            action="whatsapp_update_tenant_success"
        )
    except Exception as e:
        logger.error(
            "Erro ao atualizar tenant",
            tenant_id=str(tenant.id),
            error=str(e),
            action="whatsapp_update_tenant_error"
        )
        # Não falhar aqui, instância foi criada com sucesso

    logger.info(
        "Conexão WhatsApp iniciada com sucesso",
        tenant_id=str(tenant.id),
        instance_name=instance_name,
        action="whatsapp_connect_success"
    )

    return {"status": "created", "instance_name": instance_name}

@router.get("/status")
async def get_status(
    tenant: Tenant = Depends(get_current_tenant),
    provider: EvolutionProvider = Depends(get_whatsapp_provider),
):
    logger.info(
        "Verificando status WhatsApp",
        tenant_id=str(tenant.id),
        instance_id=tenant.evolution_instance_id,
        action="whatsapp_status_check"
    )
    
    if not tenant.evolution_instance_id:
        logger.info(
            "Nenhuma instância configurada",
            tenant_id=str(tenant.id),
            action="whatsapp_status_disconnected"
        )
        return {"status": "disconnected"}

    try:
        status = await provider.get_connection_status(tenant.evolution_instance_id)
        logger.info(
            "Status WhatsApp verificado",
            tenant_id=str(tenant.id),
            instance_id=tenant.evolution_instance_id,
            status=status.value,
            action="whatsapp_status_success"
        )
    except Exception as e:
        logger.error(
            "Erro ao verificar status WhatsApp",
            tenant_id=str(tenant.id),
            instance_id=tenant.evolution_instance_id,
            error=str(e),
            action="whatsapp_status_error"
        )
        # Retornar status desconhecido ao invés de falhar
        return {"status": "unknown", "error": str(e)}
    
    # Sync with DB if needed
    # tenant_service.update_tenant(tenant.id, TenantUpdate(whatsapp_status=status.value))
    
    return {"status": status}

@router.get("/qrcode")
async def get_qrcode(
    tenant: Tenant = Depends(get_current_tenant),
    provider: EvolutionProvider = Depends(get_whatsapp_provider),
):
    logger.info(
        "Solicitando QR Code WhatsApp",
        tenant_id=str(tenant.id),
        instance_id=tenant.evolution_instance_id,
        action="whatsapp_qrcode_request"
    )
    
    if not tenant.evolution_instance_id:
        logger.error(
            "Tentativa de obter QR Code sem instância",
            tenant_id=str(tenant.id),
            action="whatsapp_qrcode_no_instance"
        )
        raise HTTPException(status_code=400, detail="Instance not created. Call /connect first.")
    
    try:
        qr_data = await provider.get_qr_code(tenant.evolution_instance_id)
        
        if not qr_data:
            logger.info(
                "QR Code não disponível",
                tenant_id=str(tenant.id),
                instance_id=tenant.evolution_instance_id,
                action="whatsapp_qrcode_unavailable"
            )
            return {"qrcode": None, "message": "No QR Code available (maybe connected?)"}
        
        logger.info(
            "QR Code obtido com sucesso",
            tenant_id=str(tenant.id),
            instance_id=tenant.evolution_instance_id,
            qr_type=qr_data.type,
            action="whatsapp_qrcode_success"
        )
        
        return {"qrcode": qr_data.code, "type": qr_data.type}
        
    except Exception as e:
        logger.error(
            "Erro ao obter QR Code",
            tenant_id=str(tenant.id),
            instance_id=tenant.evolution_instance_id,
            error=str(e),
            action="whatsapp_qrcode_error"
        )
        raise HTTPException(status_code=500, detail=f"Error getting QR Code: {str(e)}")

@router.post("/disconnect")
async def disconnect_whatsapp(
    tenant: Tenant = Depends(get_current_tenant),
    provider: EvolutionProvider = Depends(get_whatsapp_provider),
    tenant_service: TenantService = Depends()
):
    logger.info(
        "Iniciando desconexão WhatsApp",
        tenant_id=str(tenant.id),
        instance_id=tenant.evolution_instance_id,
        action="whatsapp_disconnect_start"
    )
    
    if not tenant.evolution_instance_id:
        logger.warning(
            "Tentativa de desconexão sem instância",
            tenant_id=str(tenant.id),
            action="whatsapp_disconnect_no_instance"
        )
        raise HTTPException(status_code=400, detail="No instance to disconnect")
        
    try:
        # 1. Logout/Delete instance from Evolution
        logger.info(
            "Deletando instância Evolution API",
            tenant_id=str(tenant.id),
            instance_id=tenant.evolution_instance_id,
            action="whatsapp_delete_instance"
        )
        await provider.delete_instance(tenant.evolution_instance_id)
        
        logger.info(
            "Instância Evolution API deletada com sucesso",
            tenant_id=str(tenant.id),
            instance_id=tenant.evolution_instance_id,
            action="whatsapp_delete_instance_success"
        )
        
        # 2. Update Tenant in DB
        update_data = TenantUpdate(
            evolution_instance_id=None,
            whatsapp_status="disconnected"
        )
        tenant_service.update_tenant(tenant.id, update_data)
        
        logger.info(
            "Tenant atualizado após desconexão",
            tenant_id=str(tenant.id),
            status="disconnected",
            action="whatsapp_disconnect_success"
        )
        
        return {"status": "success", "message": "Disconnected"}
        
    except Exception as e:
        logger.error(
            "Erro ao desconectar WhatsApp",
            tenant_id=str(tenant.id),
            instance_id=tenant.evolution_instance_id,
            error=str(e),
            action="whatsapp_disconnect_error"
        )
        raise HTTPException(status_code=500, detail=f"Error disconnecting: {str(e)}")
