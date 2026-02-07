"""
Router para endpoints de ativação e gestão de agentes IA.

Este módulo implementa os endpoints para:
- Ativação de agentes IA
- Consulta de status de ativação
- Desativação de agentes
- Validação de assinaturas

CRÍTICO: Usa affiliate_id do JWT, não subdomain.
"""

from typing import Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import UUID4

from app.api import deps
from app.api.deps import APIResponse
from app.schemas.agent_activation import (
    AgentActivationCreate, 
    AgentActivation,
    AffiliateActivationStatus,
    ActivationValidationResult
)
from app.services.agent_activation_service import AgentActivationService
from app.core.exceptions import PermissionDeniedException
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

@router.post("/activate", response_model=APIResponse)
async def activate_agent(
    *,
    activation_data: AgentActivationCreate,
    affiliate_id: UUID4 = Depends(deps.get_current_affiliate_id),
    service: AgentActivationService = Depends(AgentActivationService)
) -> Any:
    """
    Ativa um agente IA para o afiliado autenticado.
    
    CRÍTICO: Usa affiliate_id extraído do JWT, não subdomain.
    
    Args:
        activation_data: Dados para ativação do agente
        affiliate_id: ID do afiliado (extraído do JWT automaticamente)
        service: Serviço de ativação de agentes
        
    Returns:
        APIResponse: Dados da ativação criada
        
    Raises:
        HTTPException: 403 se assinatura inválida, 500 se erro interno
    """
    logger.info(f"🚀 [API] Solicitação de ativação de agente para afiliado {affiliate_id}")
    logger.info(f"   Agent Name: {activation_data.agent_name}")
    logger.info(f"   Agent Personality: {activation_data.agent_personality[:100] if activation_data.agent_personality else 'Não definida'}...")
    
    try:
        # Garantir que affiliate_id do payload corresponde ao token
        activation_data.affiliate_id = affiliate_id
        
        # Ativar agente
        activation = await service.activate_agent(affiliate_id, activation_data)
        
        logger.info(f"✅ [API] Agente ativado com sucesso para afiliado {affiliate_id}")
        logger.info(f"   Activation ID: {activation.id}")
        logger.info(f"   Tenant ID: {activation.tenant_id}")
        logger.info(f"   Status: {activation.status}")
        
        return APIResponse(
            data=activation,
            message="Agente ativado com sucesso!"
        )
        
    except PermissionDeniedException as e:
        logger.warning(f"❌ [API] Permissão negada para afiliado {affiliate_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Assinatura inválida: {str(e)}"
        )
    except Exception as e:
        logger.error(f"💥 [API] Erro ao ativar agente para afiliado {affiliate_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno: {str(e)}"
        )

@router.get("/status", response_model=APIResponse)
async def get_activation_status(
    *,
    affiliate_id: UUID4 = Depends(deps.get_current_affiliate_id),
    service: AgentActivationService = Depends(AgentActivationService)
) -> Any:
    """
    Obtém o status de ativação do agente para o afiliado autenticado.
    
    Args:
        affiliate_id: ID do afiliado (extraído do JWT automaticamente)
        service: Serviço de ativação de agentes
        
    Returns:
        APIResponse: Status detalhado da ativação
    """
    logger.debug(f"🔍 [API] Consultando status de ativação para afiliado {affiliate_id}")
    
    try:
        status_info = await service.get_activation_status(affiliate_id)
        
        logger.debug(f"📊 [API] Status obtido para afiliado {affiliate_id}: {status_info.status if status_info.status else 'Sem ativação'}")
        
        return APIResponse(
            data=status_info,
            message="Status obtido com sucesso"
        )
        
    except Exception as e:
        logger.error(f"💥 [API] Erro ao obter status para afiliado {affiliate_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno: {str(e)}"
        )

@router.post("/deactivate", response_model=APIResponse)
async def deactivate_agent(
    *,
    reason: str = "Desativado pelo usuário",
    affiliate_id: UUID4 = Depends(deps.get_current_affiliate_id),
    service: AgentActivationService = Depends(AgentActivationService)
) -> Any:
    """
    Desativa o agente IA do afiliado autenticado.
    
    Args:
        reason: Motivo da desativação
        affiliate_id: ID do afiliado (extraído do JWT automaticamente)
        service: Serviço de ativação de agentes
        
    Returns:
        APIResponse: Confirmação da desativação
    """
    logger.info(f"🔄 [API] Solicitação de desativação de agente para afiliado {affiliate_id}")
    logger.info(f"   Motivo: {reason}")
    
    try:
        success = await service.deactivate_agent(affiliate_id, reason)
        
        if success:
            logger.info(f"✅ [API] Agente desativado com sucesso para afiliado {affiliate_id}")
            return APIResponse(
                data={"deactivated": True, "reason": reason},
                message="Agente desativado com sucesso"
            )
        else:
            logger.warning(f"⚠️ [API] Nenhum agente ativo encontrado para desativar - afiliado {affiliate_id}")
            return APIResponse(
                data={"deactivated": False, "reason": "Nenhum agente ativo encontrado"},
                message="Nenhum agente ativo para desativar"
            )
        
    except Exception as e:
        logger.error(f"💥 [API] Erro ao desativar agente para afiliado {affiliate_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno: {str(e)}"
        )

@router.post("/validate", response_model=APIResponse)
async def validate_activation(
    *,
    affiliate_id: UUID4 = Depends(deps.get_current_affiliate_id),
    service: AgentActivationService = Depends(AgentActivationService)
) -> Any:
    """
    Valida e atualiza o status da ativação do agente.
    
    Útil para verificar se a assinatura ainda está válida e
    atualizar o status do agente conforme necessário.
    
    Args:
        affiliate_id: ID do afiliado (extraído do JWT automaticamente)
        service: Serviço de ativação de agentes
        
    Returns:
        APIResponse: Resultado da validação
    """
    logger.info(f"🔄 [API] Validando ativação para afiliado {affiliate_id}")
    
    try:
        validation_result = await service.validate_and_refresh_activation(affiliate_id)
        
        logger.info(f"📊 [API] Validação concluída para afiliado {affiliate_id}")
        logger.info(f"   Válida: {validation_result.is_valid}")
        logger.info(f"   Status: {validation_result.status}")
        logger.info(f"   Erros: {len(validation_result.validation_errors)}")
        logger.info(f"   Avisos: {len(validation_result.validation_warnings)}")
        
        return APIResponse(
            data=validation_result,
            message="Validação concluída"
        )
        
    except Exception as e:
        logger.error(f"💥 [API] Erro na validação para afiliado {affiliate_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno: {str(e)}"
        )

@router.get("/health", response_model=APIResponse)
async def agent_health_check() -> Any:
    """
    Health check específico para o módulo de agentes.
    
    Verifica se o serviço de ativação está funcionando corretamente.
    
    Returns:
        APIResponse: Status de saúde do módulo
    """
    logger.debug("🏥 [API] Health check do módulo de agentes")
    
    try:
        # Testar inicialização do serviço
        service = AgentActivationService()
        
        # Verificar conectividade com Supabase
        supabase = service.supabase
        
        # Teste simples de conectividade
        response = supabase.table("multi_agent_tenants").select("count", count="exact").limit(1).execute()
        
        health_data = {
            "module": "agent_activation",
            "status": "healthy",
            "supabase_connected": True,
            "service_initialized": True,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.debug("✅ [API] Health check do módulo de agentes: OK")
        
        return APIResponse(
            data=health_data,
            message="Módulo de agentes funcionando corretamente"
        )
        
    except Exception as e:
        logger.error(f"💥 [API] Health check falhou: {str(e)}")
        
        health_data = {
            "module": "agent_activation",
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return APIResponse(
            data=health_data,
            message=f"Módulo com problemas: {str(e)}"
        )