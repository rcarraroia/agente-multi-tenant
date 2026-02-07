"""
Serviço de Ativação de Agentes Multi-Tenant.

Este serviço gerencia o processo completo de ativação de agentes IA,
incluindo validação de assinaturas, criação de tenants e gestão do
ciclo de vida dos agentes.

CRÍTICO: Usa affiliate_id do JWT ao invés de subdomain.
"""

from uuid import UUID
import uuid
import time
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from app.db.supabase import get_supabase
from app.schemas.agent_activation import (
    AgentActivationCreate, 
    AgentActivationUpdate, 
    AgentActivation,
    ActivationStatus,
    ActivationValidationResult,
    AffiliateActivationStatus
)
from app.schemas.tenant import TenantCreate, Tenant
from app.services.tenant_service import TenantService
from app.core.exceptions import EntityNotFoundException, PermissionDeniedException
from app.core.logging import get_logger, get_structured_logger, PerformanceLogger, AuditLogger
from app.core.tenant_resolver import get_tenant_from_jwt
from postgrest.exceptions import APIError

logger = get_logger(__name__)
structured_logger = get_structured_logger(__name__)
performance_logger = PerformanceLogger()
audit_logger = AuditLogger()

class AgentActivationService:
    """
    Serviço responsável pela ativação e gestão de agentes IA.
    
    Funcionalidades principais:
    - Ativação de agentes com validação de assinatura
    - Validação contínua de status de assinatura
    - Gestão do ciclo de vida dos agentes
    - Integração com sistema de tenants
    """
    
    def __init__(self):
        self.supabase = get_supabase()
        self.tenant_service = TenantService()
        self.activations_table = "agent_activations"
        self.subscriptions_table = "multi_agent_subscriptions"
        self.services_table = "affiliate_services"

    async def activate_agent(self, affiliate_id: UUID, data: AgentActivationCreate) -> AgentActivation:
        """
        Ativa um agente IA para um afiliado específico.
        
        CRÍTICO: Usa affiliate_id do JWT, não subdomain.
        
        Args:
            affiliate_id: ID do afiliado (extraído do JWT)
            data: Dados para ativação do agente
            
        Returns:
            AgentActivation: Dados da ativação criada
            
        Raises:
            PermissionDeniedException: Se assinatura inválida
            EntityNotFoundException: Se afiliado não encontrado
        """
        start_time = time.time()
        correlation_id = str(uuid.uuid4())
        
        structured_logger.with_correlation_id(correlation_id).info(
            "Iniciando ativação de agente",
            affiliate_id=str(affiliate_id),
            agent_name=data.agent_name,
            operation="activate_agent"
        )
        
        # Log de auditoria
        audit_logger.log_user_action(
            action="agent_activation_start",
            user_id=str(affiliate_id),
            resource="agent",
            details={
                "agent_name": data.agent_name,
                "agent_personality": data.agent_personality,
                "correlation_id": correlation_id
            }
        )
        
        try:
            # 1. Validar se afiliado existe e tem assinatura válida
            validation_start = time.time()
            validation_result = await self._validate_subscription(affiliate_id)
            validation_duration = (time.time() - validation_start) * 1000
            
            # Log de performance da validação
            performance_logger.log_database_query(
                query_type="subscription_validation",
                table="multi_agent_subscriptions",
                duration_ms=validation_duration
            )
            
            if not validation_result.is_valid:
                structured_logger.warning(
                    "Assinatura inválida para ativação",
                    affiliate_id=str(affiliate_id),
                    validation_errors=validation_result.validation_errors,
                    correlation_id=correlation_id
                )
                
                audit_logger.log_user_action(
                    action="agent_activation_denied",
                    user_id=str(affiliate_id),
                    resource="agent",
                    details={
                        "reason": "invalid_subscription",
                        "errors": validation_result.validation_errors,
                        "correlation_id": correlation_id
                    }
                )
                
                raise PermissionDeniedException(
                    f"Assinatura inválida: {', '.join(validation_result.validation_errors)}"
                )
            
            # 2. Verificar se já existe ativação ativa
            existing_activation = await self._get_active_activation(affiliate_id)
            if existing_activation:
                structured_logger.info(
                    "Ativação já existe, atualizando",
                    affiliate_id=str(affiliate_id),
                    existing_activation_id=str(existing_activation.id),
                    correlation_id=correlation_id
                )
                
                result = await self._update_existing_activation(existing_activation.id, data)
                
                # Log de performance total
                total_duration = (time.time() - start_time) * 1000
                performance_logger.log_request_duration(
                    method="UPDATE",
                    path="/agent/activate",
                    duration_ms=total_duration,
                    status_code=200,
                    user_id=str(affiliate_id)
                )
                
                return result
            
            # 3. Criar ou obter tenant
            tenant_start = time.time()
            tenant = await self._ensure_tenant_exists(affiliate_id, data)
            tenant_duration = (time.time() - tenant_start) * 1000
            
            performance_logger.log_database_query(
                query_type="tenant_creation",
                table="tenants",
                duration_ms=tenant_duration
            )
            
            # 4. Criar registro de ativação
            activation_data = {
                "affiliate_id": str(affiliate_id),
                "tenant_id": str(tenant.id),
                "agent_name": data.agent_name,
                "agent_personality": data.agent_personality,
                "activation_reason": data.activation_reason or "Ativação via API",
                "subscription_id": data.subscription_id,
                "status": ActivationStatus.ACTIVE.value,
                "subscription_valid": True,
                "subscription_expires_at": validation_result.subscription_expires_at.isoformat() if validation_result.subscription_expires_at else None,
                "activated_at": datetime.utcnow().isoformat(),
                "last_validated_at": datetime.utcnow().isoformat(),
                "metadata": data.metadata or {}
            }
            
            db_start = time.time()
            response = self.supabase.table(self.activations_table)\
                .insert(activation_data)\
                .execute()
            db_duration = (time.time() - db_start) * 1000
            
            performance_logger.log_database_query(
                query_type="INSERT",
                table=self.activations_table,
                duration_ms=db_duration,
                rows_affected=1
            )
            
            if not response.data:
                raise Exception("Falha ao criar registro de ativação")
            
            activation = AgentActivation.model_validate(response.data[0])
            
            # 5. Atualizar status do tenant
            await self._update_tenant_status(tenant.id, "active")
            
            # Log de sucesso
            total_duration = (time.time() - start_time) * 1000
            
            structured_logger.info(
                "Agente ativado com sucesso",
                affiliate_id=str(affiliate_id),
                tenant_id=str(tenant.id),
                agent_name=activation.agent_name,
                activation_id=str(activation.id),
                total_duration_ms=round(total_duration, 2),
                correlation_id=correlation_id
            )
            
            # Log de auditoria de sucesso
            audit_logger.log_user_action(
                action="agent_activation_success",
                user_id=str(affiliate_id),
                resource="agent",
                details={
                    "activation_id": str(activation.id),
                    "tenant_id": str(tenant.id),
                    "agent_name": activation.agent_name,
                    "duration_ms": round(total_duration, 2),
                    "correlation_id": correlation_id
                }
            )
            
            # Log de performance total
            performance_logger.log_request_duration(
                method="POST",
                path="/agent/activate",
                duration_ms=total_duration,
                status_code=201,
                user_id=str(affiliate_id)
            )
            
            return activation
            
        except Exception as e:
            total_duration = (time.time() - start_time) * 1000
            
            structured_logger.error(
                "Erro ao ativar agente",
                affiliate_id=str(affiliate_id),
                error=str(e),
                duration_ms=round(total_duration, 2),
                correlation_id=correlation_id,
                exception=e
            )
            
            # Log de auditoria de erro
            audit_logger.log_user_action(
                action="agent_activation_failed",
                user_id=str(affiliate_id),
                resource="agent",
                details={
                    "error": str(e),
                    "duration_ms": round(total_duration, 2),
                    "correlation_id": correlation_id
                }
            )
            
            raise

    async def deactivate_agent(self, affiliate_id: UUID, reason: str = "Desativado pelo usuário") -> bool:
        """
        Desativa um agente IA de um afiliado.
        
        Args:
            affiliate_id: ID do afiliado
            reason: Motivo da desativação
            
        Returns:
            bool: True se desativado com sucesso
        """
        logger.info(f"🔄 Desativando agente para afiliado {affiliate_id}")
        
        try:
            # Buscar ativação ativa
            activation = await self._get_active_activation(affiliate_id)
            if not activation:
                logger.warning(f"⚠️ Nenhuma ativação ativa encontrada para afiliado {affiliate_id}")
                return False
            
            # Atualizar status
            update_data = {
                "status": ActivationStatus.SUSPENDED.value,
                "deactivated_at": datetime.utcnow().isoformat(),
                "deactivation_reason": reason,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            response = self.supabase.table(self.activations_table)\
                .update(update_data)\
                .eq("id", str(activation.id))\
                .execute()
            
            if response.data:
                # Atualizar tenant também
                await self._update_tenant_status(activation.tenant_id, "suspended")
                logger.info(f"✅ Agente desativado para afiliado {affiliate_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"💥 Erro ao desativar agente para afiliado {affiliate_id}: {str(e)}")
            return False

    async def get_activation_status(self, affiliate_id: UUID) -> AffiliateActivationStatus:
        """
        Obtém o status de ativação de um afiliado.
        
        Args:
            affiliate_id: ID do afiliado
            
        Returns:
            AffiliateActivationStatus: Status detalhado da ativação
        """
        logger.debug(f"🔍 Verificando status de ativação para afiliado {affiliate_id}")
        
        try:
            # Buscar ativação mais recente
            response = self.supabase.table(self.activations_table)\
                .select("*")\
                .eq("affiliate_id", str(affiliate_id))\
                .order("created_at", desc=True)\
                .limit(1)\
                .execute()
            
            if not response.data:
                return AffiliateActivationStatus(
                    affiliate_id=affiliate_id,
                    has_active_agent=False,
                    can_reactivate=True
                )
            
            activation_data = response.data[0]
            activation = AgentActivation.model_validate(activation_data)
            
            # Calcular dias até expiração
            days_until_expiration = None
            if activation.subscription_expires_at:
                delta = activation.subscription_expires_at - datetime.utcnow()
                days_until_expiration = max(0, delta.days)
            
            return AffiliateActivationStatus(
                affiliate_id=affiliate_id,
                has_active_agent=activation.status == ActivationStatus.ACTIVE,
                agent_name=activation.agent_name,
                agent_personality=activation.agent_personality,
                status=activation.status,
                activated_at=activation.activated_at,
                expires_at=activation.subscription_expires_at,
                tenant_id=activation.tenant_id,
                subscription_valid=activation.subscription_valid,
                days_until_expiration=days_until_expiration,
                can_reactivate=activation.status in [ActivationStatus.SUSPENDED, ActivationStatus.EXPIRED],
                reactivation_blocked_reason=activation.deactivation_reason if activation.status == ActivationStatus.FAILED else None
            )
            
        except Exception as e:
            logger.error(f"💥 Erro ao verificar status para afiliado {affiliate_id}: {str(e)}")
            return AffiliateActivationStatus(
                affiliate_id=affiliate_id,
                has_active_agent=False,
                can_reactivate=False,
                reactivation_blocked_reason=f"Erro interno: {str(e)}"
            )

    async def validate_and_refresh_activation(self, affiliate_id: UUID) -> ActivationValidationResult:
        """
        Valida e atualiza o status de uma ativação existente.
        
        Args:
            affiliate_id: ID do afiliado
            
        Returns:
            ActivationValidationResult: Resultado da validação
        """
        logger.debug(f"🔄 Validando ativação para afiliado {affiliate_id}")
        
        try:
            # Validar assinatura atual
            validation_result = await self._validate_subscription(affiliate_id)
            
            # Buscar ativação existente
            activation = await self._get_active_activation(affiliate_id)
            
            if activation:
                # Atualizar status baseado na validação
                new_status = ActivationStatus.ACTIVE if validation_result.is_valid else ActivationStatus.EXPIRED
                
                if activation.status != new_status:
                    await self._update_activation_status(activation.id, new_status, validation_result)
                    logger.info(f"📊 Status atualizado para afiliado {affiliate_id}: {activation.status} → {new_status}")
                
                # Atualizar última validação
                await self._update_last_validation(activation.id)
            
            return validation_result
            
        except Exception as e:
            logger.error(f"💥 Erro na validação para afiliado {affiliate_id}: {str(e)}")
            return ActivationValidationResult(
                is_valid=False,
                status=ActivationStatus.FAILED,
                affiliate_id=affiliate_id,
                validation_errors=[f"Erro interno: {str(e)}"],
                last_validated_at=datetime.utcnow()
            )

    # ============================================
    # MÉTODOS PRIVADOS
    # ============================================

    async def _validate_subscription(self, affiliate_id: UUID) -> ActivationValidationResult:
        """Valida se o afiliado tem assinatura ativa."""
        logger.debug(f"🔍 Validando assinatura para afiliado {affiliate_id}")
        
        errors = []
        warnings = []
        subscription_valid = False
        subscription_expires_at = None
        
        try:
            # 1. Verificar assinatura na tabela multi_agent_subscriptions
            subscription_response = self.supabase.table(self.subscriptions_table)\
                .select("*")\
                .eq("affiliate_id", str(affiliate_id))\
                .eq("status", "active")\
                .order("created_at", desc=True)\
                .limit(1)\
                .execute()
            
            if subscription_response.data:
                subscription = subscription_response.data[0]
                next_due_date = datetime.fromisoformat(subscription["next_due_date"].replace("Z", "+00:00"))
                
                if next_due_date > datetime.utcnow():
                    subscription_valid = True
                    subscription_expires_at = next_due_date
                    logger.debug(f"✅ Assinatura válida até {next_due_date}")
                else:
                    errors.append(f"Assinatura expirada em {next_due_date}")
            else:
                # 2. Fallback: verificar na tabela affiliate_services
                service_response = self.supabase.table(self.services_table)\
                    .select("*")\
                    .eq("affiliate_id", str(affiliate_id))\
                    .eq("service_type", "agente_ia")\
                    .eq("status", "active")\
                    .order("created_at", desc=True)\
                    .limit(1)\
                    .execute()
                
                if service_response.data:
                    service = service_response.data[0]
                    if service.get("expires_at"):
                        expires_at = datetime.fromisoformat(service["expires_at"].replace("Z", "+00:00"))
                        
                        if expires_at > datetime.utcnow():
                            subscription_valid = True
                            subscription_expires_at = expires_at
                            warnings.append("Usando serviço de afiliado como fallback")
                            logger.debug(f"✅ Serviço válido até {expires_at}")
                        else:
                            errors.append(f"Serviço expirado em {expires_at}")
                    else:
                        subscription_valid = True  # Serviço sem expiração
                        warnings.append("Serviço sem data de expiração definida")
                else:
                    errors.append("Nenhuma assinatura ou serviço ativo encontrado")
            
            is_valid = subscription_valid and len(errors) == 0
            status = ActivationStatus.ACTIVE if is_valid else ActivationStatus.EXPIRED
            
            return ActivationValidationResult(
                is_valid=is_valid,
                status=status,
                affiliate_id=affiliate_id,
                subscription_valid=subscription_valid,
                subscription_expires_at=subscription_expires_at,
                validation_errors=errors,
                validation_warnings=warnings,
                last_validated_at=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"💥 Erro na validação de assinatura: {str(e)}")
            return ActivationValidationResult(
                is_valid=False,
                status=ActivationStatus.FAILED,
                affiliate_id=affiliate_id,
                validation_errors=[f"Erro interno: {str(e)}"],
                last_validated_at=datetime.utcnow()
            )

    async def _get_active_activation(self, affiliate_id: UUID) -> Optional[AgentActivation]:
        """Busca ativação ativa para um afiliado."""
        try:
            response = self.supabase.table(self.activations_table)\
                .select("*")\
                .eq("affiliate_id", str(affiliate_id))\
                .in_("status", [ActivationStatus.ACTIVE.value, ActivationStatus.PENDING.value])\
                .order("created_at", desc=True)\
                .limit(1)\
                .execute()
            
            if response.data:
                return AgentActivation.model_validate(response.data[0])
            
            return None
            
        except Exception as e:
            logger.error(f"💥 Erro ao buscar ativação ativa: {str(e)}")
            return None

    async def _ensure_tenant_exists(self, affiliate_id: UUID, data: AgentActivationCreate) -> Tenant:
        """Garante que existe um tenant para o afiliado."""
        try:
            # Tentar buscar tenant existente
            try:
                tenant = self.tenant_service.get_by_affiliate_id(affiliate_id)
                logger.debug(f"✅ Tenant existente encontrado: {tenant.id}")
                return tenant
            except EntityNotFoundException:
                pass
            
            # Criar novo tenant
            tenant_data = TenantCreate(
                affiliate_id=affiliate_id,
                agent_name=data.agent_name,
                agent_personality=data.agent_personality
            )
            
            tenant = self.tenant_service.create_tenant(tenant_data)
            logger.info(f"✅ Novo tenant criado: {tenant.id}")
            return tenant
            
        except Exception as e:
            logger.error(f"💥 Erro ao garantir tenant: {str(e)}")
            raise

    async def _update_existing_activation(self, activation_id: UUID, data: AgentActivationCreate) -> AgentActivation:
        """Atualiza uma ativação existente."""
        update_data = {
            "agent_name": data.agent_name,
            "agent_personality": data.agent_personality,
            "status": ActivationStatus.ACTIVE.value,
            "activated_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        if data.metadata:
            update_data["metadata"] = data.metadata
        
        response = self.supabase.table(self.activations_table)\
            .update(update_data)\
            .eq("id", str(activation_id))\
            .execute()
        
        if not response.data:
            raise Exception("Falha ao atualizar ativação existente")
        
        return AgentActivation.model_validate(response.data[0])

    async def _update_tenant_status(self, tenant_id: UUID, status: str):
        """Atualiza o status de um tenant."""
        try:
            self.tenant_service.update_tenant(tenant_id, {"status": status})
        except Exception as e:
            logger.warning(f"⚠️ Erro ao atualizar status do tenant {tenant_id}: {str(e)}")

    async def _update_activation_status(self, activation_id: UUID, status: ActivationStatus, validation_result: ActivationValidationResult):
        """Atualiza o status de uma ativação."""
        update_data = {
            "status": status.value,
            "subscription_valid": validation_result.subscription_valid,
            "subscription_expires_at": validation_result.subscription_expires_at.isoformat() if validation_result.subscription_expires_at else None,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        if status == ActivationStatus.EXPIRED:
            update_data["deactivated_at"] = datetime.utcnow().isoformat()
            update_data["deactivation_reason"] = "Assinatura expirada"
        
        self.supabase.table(self.activations_table)\
            .update(update_data)\
            .eq("id", str(activation_id))\
            .execute()

    async def _update_last_validation(self, activation_id: UUID):
        """Atualiza timestamp da última validação."""
        self.supabase.table(self.activations_table)\
            .update({"last_validated_at": datetime.utcnow().isoformat()})\
            .eq("id", str(activation_id))\
            .execute()