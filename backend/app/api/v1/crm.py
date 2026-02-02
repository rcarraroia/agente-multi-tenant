from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import UUID4

from app.api import deps
from app.schemas.crm import (
    FunnelCreate, FunnelUpdate, Funnel, FunnelWithStages,
    StageCreate, StageUpdate, Stage, StageReorderItem,
    MoveConversationRequest, StageHistory
)
from app.services.crm_service import CRMService
from app.schemas.tenant import Tenant

router = APIRouter()

# Dependency for CRMService
def get_crm_service() -> CRMService:
    return CRMService()

# ============ FUNNELS ============

@router.post("/funnels", response_model=Funnel, status_code=status.HTTP_201_CREATED)
def create_funnel(
    data: FunnelCreate,
    tenant: Tenant = Depends(deps.get_current_tenant),
    service: CRMService = Depends(get_crm_service)
):
    """
    Criar novo funil de vendas.
    Limite: 5 funis por inquilino.
    """
    return service.create_funnel(tenant_id=tenant.id, data=data)

@router.get("/funnels", response_model=List[Funnel])
def list_funnels(
    tenant: Tenant = Depends(deps.get_current_tenant),
    service: CRMService = Depends(get_crm_service)
):
    """Listar todos os funis do inquilino."""
    return service.list_funnels(tenant_id=tenant.id)

@router.get("/funnels/{funnel_id}", response_model=FunnelWithStages)
def get_funnel(
    funnel_id: UUID4,
    tenant: Tenant = Depends(deps.get_current_tenant),
    service: CRMService = Depends(get_crm_service)
):
    """Obter detalhes do funil incluindo suas etapas."""
    return service.get_funnel_with_stages(tenant_id=tenant.id, funnel_id=funnel_id)

@router.patch("/funnels/{funnel_id}", response_model=Funnel)
def update_funnel(
    funnel_id: UUID4,
    data: FunnelUpdate,
    tenant: Tenant = Depends(deps.get_current_tenant),
    service: CRMService = Depends(get_crm_service)
):
    """Atualizar nome ou descrição do funil."""
    return service.update_funnel(tenant_id=tenant.id, funnel_id=funnel_id, data=data)

@router.delete("/funnels/{funnel_id}")
def delete_funnel(
    funnel_id: UUID4,
    move_to_funnel_id: Optional[UUID4] = Query(None, description="ID do funil para onde mover as conversas existentes"),
    tenant: Tenant = Depends(deps.get_current_tenant),
    service: CRMService = Depends(get_crm_service)
):
    """
    Deletar funil.
    Se houver conversas, é obrigatório fornecer 'move_to_funnel_id' para migração.
    O funil padrão não pode ser deletado.
    """
    return service.delete_funnel(tenant_id=tenant.id, funnel_id=funnel_id, move_to_funnel_id=move_to_funnel_id)

# ============ STAGES ============

@router.post("/stages", response_model=Stage, status_code=status.HTTP_201_CREATED)
def create_stage(
    data: StageCreate,
    tenant: Tenant = Depends(deps.get_current_tenant),
    service: CRMService = Depends(get_crm_service)
):
    """Criar nova etapa em um funil."""
    return service.create_stage(tenant_id=tenant.id, data=data)

@router.patch("/stages/reorder")
def reorder_stages(
    items: List[StageReorderItem],
    funnel_id: UUID4 = Query(..., description="ID do funil a ser reordenado"),
    tenant: Tenant = Depends(deps.get_current_tenant),
    service: CRMService = Depends(get_crm_service)
):
    """Reordenar etapas de um funil."""
    return service.reorder_stages(tenant_id=tenant.id, funnel_id=funnel_id, items=items)

@router.patch("/stages/{stage_id}", response_model=Stage)
def update_stage(
    stage_id: UUID4,
    data: StageUpdate,
    tenant: Tenant = Depends(deps.get_current_tenant),
    service: CRMService = Depends(get_crm_service)
):
    """Atualizar etapa (nome, cor)."""
    return service.update_stage(tenant_id=tenant.id, stage_id=stage_id, data=data)

@router.delete("/stages/{stage_id}")
def delete_stage(
    stage_id: UUID4,
    move_to_stage_id: Optional[UUID4] = Query(None, description="ID da etapa para onde mover as conversas existentes"),
    tenant: Tenant = Depends(deps.get_current_tenant),
    service: CRMService = Depends(get_crm_service)
):
    """
    Deletar etapa.
    Se houver conversas, é obrigatório fornecer 'move_to_stage_id'.
    Realiza reordenação automática das etapas subsequentes.
    """
    return service.delete_stage(tenant_id=tenant.id, stage_id=stage_id, move_to_stage_id=move_to_stage_id)

# ============ CONVERSATION MOVEMENT ============

@router.post("/conversations/{conversation_id}/move")
def move_conversation(
    conversation_id: UUID4,
    data: MoveConversationRequest,
    tenant: Tenant = Depends(deps.get_current_tenant),
    user_id: str = Depends(deps.get_current_user_id),
    service: CRMService = Depends(get_crm_service)
):
    """
    Mover conversa para outra etapa.
    Valida se a etapa pertence ao mesmo funil.
    Registra histórico da movimentação.
    """
    return service.move_conversation(
        tenant_id=tenant.id, 
        conversation_id=conversation_id, 
        request=data, 
        moved_by=UUID4(user_id)
    )

@router.get("/conversations/{conversation_id}/history", response_model=List[StageHistory])
def get_conversation_history(
    conversation_id: UUID4,
    tenant: Tenant = Depends(deps.get_current_tenant),
    service: CRMService = Depends(get_crm_service)
):
    """Obter histórico de movimentações da conversa no CRM."""
    return service.get_conversation_history(tenant_id=tenant.id, conversation_id=conversation_id)
