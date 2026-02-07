"""
Subscription Synchronizer Service.

Serviço responsável por sincronizar e unificar dados entre
affiliate_services e multi_agent_subscriptions, garantindo
consistência e integridade dos dados de assinatura.
"""

from uuid import UUID
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta, timezone
from app.db.supabase import get_supabase
from app.schemas.subscription_sync import (
    UnifiedSubscription,
    UnifiedSubscriptionStatus,
    SubscriptionSource,
    SubscriptionConflict,
    SubscriptionSyncResult,
    SubscriptionSyncConfig,
    SubscriptionValidationResult,
    SubscriptionMigrationPlan
)
from app.schemas.tenant import TenantCreate, Tenant
from app.services.tenant_service import TenantService
from app.core.exceptions import EntityNotFoundException, ValidationException
from app.core.logging import get_logger, get_structured_logger, PerformanceLogger, AuditLogger
from postgrest.exceptions import APIError

logger = get_logger(__name__)
structured_logger = get_structured_logger(__name__)
performance_logger = PerformanceLogger()
audit_logger = AuditLogger()

class SubscriptionSynchronizer:
    """
    Serviço de sincronização de assinaturas.
    
    Responsável por:
    - Unificar dados entre affiliate_services e multi_agent_subscriptions
    - Resolver conflitos de dados automaticamente
    - Manter consistência entre as tabelas
    - Fornecer visão unificada das assinaturas
    """
    
    def __init__(self):
        self.supabase = get_supabase()
        self.tenant_service = TenantService()
        
        # Tabelas
        self.services_table = "affiliate_services"
        self.subscriptions_table = "multi_agent_subscriptions"
        self.tenants_table = "multi_agent_tenants"
        self.affiliates_table = "affiliates"

    async def synchronize_all(self, config: SubscriptionSyncConfig = None) -> SubscriptionSyncResult:
        """
        Sincroniza todas as assinaturas entre as tabelas.
        
        Args:
            config: Configuração da sincronização
            
        Returns:
            SubscriptionSyncResult: Resultado da sincronização
        """
        if config is None:
            config = SubscriptionSyncConfig()
        
        logger.info("🔄 Iniciando sincronização completa de assinaturas")
        logger.info(f"   Configuração: dry_run={config.dry_run}, batch_size={config.batch_size}")
        
        start_time = datetime.now(timezone.utc)
        result = SubscriptionSyncResult(
            total_processed=0,
            successful_syncs=0,
            conflicts_found=0,
            errors_encountered=0,
            execution_time_seconds=0.0,
            started_at=start_time,
            completed_at=start_time
        )
        
        try:
            # 1. Obter todos os afiliados com serviços ou assinaturas
            affiliate_ids = await self._get_all_subscription_affiliates()
            result.total_processed = len(affiliate_ids)
            
            logger.info(f"📊 Encontrados {len(affiliate_ids)} afiliados para sincronizar")
            
            # 2. Processar em lotes
            for i in range(0, len(affiliate_ids), config.batch_size):
                batch = affiliate_ids[i:i + config.batch_size]
                logger.debug(f"🔄 Processando lote {i//config.batch_size + 1}: {len(batch)} afiliados")
                
                for affiliate_id in batch:
                    try:
                        sync_result = await self._synchronize_affiliate(affiliate_id, config)
                        
                        if sync_result["success"]:
                            result.successful_syncs += 1
                            result.synced_affiliates.append(affiliate_id)
                        
                        if sync_result["conflicts"]:
                            result.conflicts_found += len(sync_result["conflicts"])
                            result.conflicted_affiliates.append(affiliate_id)
                            
                            # Contar tipos de conflitos
                            for conflict in sync_result["conflicts"]:
                                conflict_type = conflict.field_name
                                result.conflict_summary[conflict_type] = result.conflict_summary.get(conflict_type, 0) + 1
                        
                    except Exception as e:
                        logger.error(f"💥 Erro ao sincronizar afiliado {affiliate_id}: {str(e)}")
                        result.errors_encountered += 1
                        result.error_affiliates.append(affiliate_id)
            
            # 3. Finalizar
            end_time = datetime.now(timezone.utc)
            result.completed_at = end_time
            result.execution_time_seconds = (end_time - start_time).total_seconds()
            
            logger.info("✅ Sincronização completa finalizada")
            logger.info(f"   Processados: {result.total_processed}")
            logger.info(f"   Sucessos: {result.successful_syncs}")
            logger.info(f"   Conflitos: {result.conflicts_found}")
            logger.info(f"   Erros: {result.errors_encountered}")
            logger.info(f"   Tempo: {result.execution_time_seconds:.2f}s")
            
            return result
            
        except Exception as e:
            logger.error(f"💥 Erro na sincronização completa: {str(e)}")
            result.errors_encountered += 1
            result.completed_at = datetime.now(timezone.utc)
            result.execution_time_seconds = (result.completed_at - start_time).total_seconds()
            raise

    async def get_unified_subscription(self, affiliate_id: UUID) -> Optional[UnifiedSubscription]:
        """
        Obtém a visão unificada da assinatura de um afiliado.
        
        Args:
            affiliate_id: ID do afiliado
            
        Returns:
            UnifiedSubscription: Dados unificados ou None se não encontrado
        """
        logger.debug(f"🔍 Obtendo assinatura unificada para afiliado {affiliate_id}")
        
        try:
            # 1. Buscar dados em affiliate_services
            service_data = await self._get_affiliate_service(affiliate_id)
            
            # 2. Buscar dados em multi_agent_subscriptions
            subscription_data = await self._get_multi_agent_subscription(affiliate_id)
            
            # 3. Buscar tenant
            tenant_data = await self._get_tenant_by_affiliate(affiliate_id)
            
            # 4. Se não há dados em nenhuma tabela, retornar None
            if not service_data and not subscription_data:
                logger.debug(f"❌ Nenhuma assinatura encontrada para afiliado {affiliate_id}")
                return None
            
            # 5. Unificar dados
            unified = await self._create_unified_subscription(
                affiliate_id=affiliate_id,
                service_data=service_data,
                subscription_data=subscription_data,
                tenant_data=tenant_data
            )
            
            logger.debug(f"✅ Assinatura unificada criada para afiliado {affiliate_id}")
            logger.debug(f"   Status: {unified.status}")
            logger.debug(f"   Fonte primária: {unified.primary_source}")
            logger.debug(f"   Conflitos: {len(unified.conflicts)}")
            
            return unified
            
        except Exception as e:
            logger.error(f"💥 Erro ao obter assinatura unificada para {affiliate_id}: {str(e)}")
            return None

    async def validate_consistency(self) -> SubscriptionValidationResult:
        """
        Valida a consistência entre as tabelas de assinatura.
        
        Returns:
            SubscriptionValidationResult: Resultado da validação
        """
        logger.info("🔍 Iniciando validação de consistência de assinaturas")
        
        result = SubscriptionValidationResult(
            is_consistent=True,
            total_checked=0,
            inconsistencies_found=0,
            validated_at=datetime.now(timezone.utc)
        )
        
        try:
            # 1. Obter todos os afiliados
            affiliate_ids = await self._get_all_subscription_affiliates()
            result.total_checked = len(affiliate_ids)
            
            logger.info(f"📊 Validando consistência para {len(affiliate_ids)} afiliados")
            
            # 2. Verificar cada afiliado
            for affiliate_id in affiliate_ids:
                try:
                    inconsistencies = await self._check_affiliate_consistency(affiliate_id)
                    
                    if inconsistencies:
                        result.is_consistent = False
                        result.inconsistencies_found += len(inconsistencies)
                        
                        # Categorizar inconsistências
                        for inconsistency in inconsistencies:
                            if inconsistency["type"] == "missing_service":
                                result.missing_in_services.append(affiliate_id)
                            elif inconsistency["type"] == "missing_subscription":
                                result.missing_in_subscriptions.append(affiliate_id)
                            elif inconsistency["type"] == "status_mismatch":
                                result.status_mismatches.append(affiliate_id)
                            elif inconsistency["type"] == "date_conflict":
                                result.date_conflicts.append(affiliate_id)
                            
                            result.validation_errors.append(
                                f"Afiliado {affiliate_id}: {inconsistency['description']}"
                            )
                
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao validar afiliado {affiliate_id}: {str(e)}")
                    result.validation_warnings.append(
                        f"Erro na validação do afiliado {affiliate_id}: {str(e)}"
                    )
            
            # 3. Resumo
            if result.is_consistent:
                logger.info("✅ Validação concluída: dados consistentes")
            else:
                logger.warning(f"⚠️ Validação concluída: {result.inconsistencies_found} inconsistências encontradas")
                logger.warning(f"   Faltando em services: {len(result.missing_in_services)}")
                logger.warning(f"   Faltando em subscriptions: {len(result.missing_in_subscriptions)}")
                logger.warning(f"   Conflitos de status: {len(result.status_mismatches)}")
                logger.warning(f"   Conflitos de data: {len(result.date_conflicts)}")
            
            return result
            
        except Exception as e:
            logger.error(f"💥 Erro na validação de consistência: {str(e)}")
            result.validation_errors.append(f"Erro geral: {str(e)}")
            result.is_consistent = False
            return result

    # ============================================
    # MÉTODOS PRIVADOS
    # ============================================

    async def _get_all_subscription_affiliates(self) -> List[UUID]:
        """Obtém todos os afiliados que têm serviços ou assinaturas."""
        try:
            # Afiliados com serviços
            services_response = self.supabase.table(self.services_table)\
                .select("affiliate_id")\
                .eq("service_type", "agente_ia")\
                .execute()
            
            service_affiliates = {UUID(row["affiliate_id"]) for row in services_response.data}
            
            # Afiliados com assinaturas
            subscriptions_response = self.supabase.table(self.subscriptions_table)\
                .select("affiliate_id")\
                .execute()
            
            subscription_affiliates = {UUID(row["affiliate_id"]) for row in subscriptions_response.data}
            
            # União dos dois conjuntos
            all_affiliates = list(service_affiliates | subscription_affiliates)
            
            logger.debug(f"📊 Afiliados encontrados:")
            logger.debug(f"   Com serviços: {len(service_affiliates)}")
            logger.debug(f"   Com assinaturas: {len(subscription_affiliates)}")
            logger.debug(f"   Total único: {len(all_affiliates)}")
            
            return all_affiliates
            
        except Exception as e:
            logger.error(f"💥 Erro ao obter afiliados: {str(e)}")
            return []

    async def _synchronize_affiliate(self, affiliate_id: UUID, config: SubscriptionSyncConfig) -> Dict[str, Any]:
        """Sincroniza dados de um afiliado específico."""
        logger.debug(f"🔄 Sincronizando afiliado {affiliate_id}")
        
        result = {
            "success": False,
            "conflicts": [],
            "actions_taken": [],
            "errors": []
        }
        
        try:
            # 1. Obter dados atuais
            service_data = await self._get_affiliate_service(affiliate_id)
            subscription_data = await self._get_multi_agent_subscription(affiliate_id)
            tenant_data = await self._get_tenant_by_affiliate(affiliate_id)
            
            # 2. Identificar conflitos
            conflicts = await self._identify_conflicts(service_data, subscription_data)
            result["conflicts"] = conflicts
            
            # 3. Resolver conflitos se configurado
            if config.resolve_conflicts_automatically and conflicts:
                resolution_actions = await self._resolve_conflicts(
                    affiliate_id, conflicts, config, dry_run=config.dry_run
                )
                result["actions_taken"].extend(resolution_actions)
            
            # 4. Criar tenant se necessário
            if config.create_missing_tenants and not tenant_data and subscription_data:
                if not config.dry_run:
                    tenant_action = await self._create_missing_tenant(affiliate_id, subscription_data)
                    result["actions_taken"].append(tenant_action)
                else:
                    result["actions_taken"].append(f"[DRY RUN] Criaria tenant para afiliado {affiliate_id}")
            
            result["success"] = True
            
        except Exception as e:
            logger.error(f"💥 Erro na sincronização do afiliado {affiliate_id}: {str(e)}")
            result["errors"].append(str(e))
        
        return result

    async def _get_affiliate_service(self, affiliate_id: UUID) -> Optional[Dict[str, Any]]:
        """Busca dados do afiliado na tabela affiliate_services."""
        try:
            response = self.supabase.table(self.services_table)\
                .select("*")\
                .eq("affiliate_id", str(affiliate_id))\
                .eq("service_type", "agente_ia")\
                .order("created_at", desc=True)\
                .limit(1)\
                .execute()
            
            return response.data[0] if response.data else None
            
        except Exception as e:
            logger.error(f"💥 Erro ao buscar serviço do afiliado {affiliate_id}: {str(e)}")
            return None

    async def _get_multi_agent_subscription(self, affiliate_id: UUID) -> Optional[Dict[str, Any]]:
        """Busca dados do afiliado na tabela multi_agent_subscriptions."""
        try:
            response = self.supabase.table(self.subscriptions_table)\
                .select("*")\
                .eq("affiliate_id", str(affiliate_id))\
                .order("created_at", desc=True)\
                .limit(1)\
                .execute()
            
            return response.data[0] if response.data else None
            
        except Exception as e:
            logger.error(f"💥 Erro ao buscar assinatura do afiliado {affiliate_id}: {str(e)}")
            return None

    async def _get_tenant_by_affiliate(self, affiliate_id: UUID) -> Optional[Dict[str, Any]]:
        """Busca tenant do afiliado."""
        try:
            response = self.supabase.table(self.tenants_table)\
                .select("*")\
                .eq("affiliate_id", str(affiliate_id))\
                .execute()
            
            return response.data[0] if response.data else None
            
        except Exception as e:
            logger.error(f"💥 Erro ao buscar tenant do afiliado {affiliate_id}: {str(e)}")
            return None

    async def _create_unified_subscription(
        self, 
        affiliate_id: UUID,
        service_data: Optional[Dict[str, Any]],
        subscription_data: Optional[Dict[str, Any]],
        tenant_data: Optional[Dict[str, Any]]
    ) -> UnifiedSubscription:
        """Cria representação unificada dos dados."""
        
        # Determinar fonte primária
        if subscription_data and service_data:
            primary_source = SubscriptionSource.MULTI_AGENT_SUBSCRIPTIONS
        elif subscription_data:
            primary_source = SubscriptionSource.MULTI_AGENT_SUBSCRIPTIONS
        elif service_data:
            primary_source = SubscriptionSource.AFFILIATE_SERVICES
        else:
            primary_source = SubscriptionSource.UNIFIED
        
        # Determinar status unificado
        unified_status = await self._determine_unified_status(service_data, subscription_data)
        
        # Identificar conflitos
        conflicts = await self._identify_conflicts(service_data, subscription_data)
        
        # Construir objeto unificado
        unified = UnifiedSubscription(
            affiliate_id=affiliate_id,
            tenant_id=UUID(tenant_data["id"]) if tenant_data else None,
            
            # Status
            status=unified_status,
            is_active=unified_status in [UnifiedSubscriptionStatus.ACTIVE, UnifiedSubscriptionStatus.TRIAL],
            
            # Dados de serviço
            service_type=service_data.get("service_type") if service_data else None,
            service_expires_at=self._parse_datetime_with_timezone(service_data["expires_at"]) if service_data and service_data.get("expires_at") else None,
            service_metadata=service_data.get("metadata") if service_data else None,
            
            # Dados de assinatura
            asaas_subscription_id=subscription_data.get("asaas_subscription_id") if subscription_data else None,
            asaas_customer_id=subscription_data.get("asaas_customer_id") if subscription_data else None,
            plan_value_cents=subscription_data.get("plan_value_cents") if subscription_data else None,
            billing_type=subscription_data.get("billing_type") if subscription_data else None,
            next_due_date=self._parse_datetime_with_timezone(subscription_data["next_due_date"]) if subscription_data and subscription_data.get("next_due_date") else None,
            
            # Metadados
            primary_source=primary_source,
            last_synced_at=datetime.now(timezone.utc),
            conflicts=conflicts,
            
            # Timestamps (usar o mais antigo)
            created_at=self._get_earliest_date(service_data, subscription_data, "created_at"),
            updated_at=self._get_latest_date(service_data, subscription_data, "updated_at")
        )
        
        return unified

    async def _determine_unified_status(
        self, 
        service_data: Optional[Dict[str, Any]], 
        subscription_data: Optional[Dict[str, Any]]
    ) -> UnifiedSubscriptionStatus:
        """Determina o status unificado baseado nos dados disponíveis."""
        
        # Priorizar dados de subscription se disponível
        if subscription_data:
            status = subscription_data.get("status", "").lower()
            if status == "active":
                return UnifiedSubscriptionStatus.ACTIVE
            elif status == "overdue":
                return UnifiedSubscriptionStatus.OVERDUE
            elif status == "canceled":
                return UnifiedSubscriptionStatus.CANCELED
            elif status == "expired":
                return UnifiedSubscriptionStatus.EXPIRED
        
        # Fallback para service_data
        if service_data:
            status = service_data.get("status", "").lower()
            if status == "active":
                return UnifiedSubscriptionStatus.ACTIVE
            elif status == "inactive":
                return UnifiedSubscriptionStatus.INACTIVE
            elif status == "trial":
                return UnifiedSubscriptionStatus.TRIAL
            elif status == "pending":
                return UnifiedSubscriptionStatus.PENDING
        
        # Default
        return UnifiedSubscriptionStatus.INACTIVE

    async def _identify_conflicts(
        self, 
        service_data: Optional[Dict[str, Any]], 
        subscription_data: Optional[Dict[str, Any]]
    ) -> List[SubscriptionConflict]:
        """Identifica conflitos entre os dados das duas tabelas."""
        conflicts = []
        
        if not service_data or not subscription_data:
            return conflicts
        
        # Verificar conflitos de status
        service_status = service_data.get("status", "").lower()
        subscription_status = subscription_data.get("status", "").lower()
        
        if service_status and subscription_status:
            # Mapear status equivalentes
            status_mapping = {
                "active": ["active"],
                "inactive": ["canceled", "expired"],
                "trial": ["active"],  # Trial pode ser considerado ativo
                "pending": ["pending"]
            }
            
            service_equivalent = status_mapping.get(service_status, [service_status])
            if subscription_status not in service_equivalent:
                conflicts.append(SubscriptionConflict(
                    field_name="status",
                    affiliate_services_value=service_status,
                    multi_agent_subscriptions_value=subscription_status,
                    recommended_resolution=f"Usar status da assinatura: {subscription_status}",
                    severity="medium"
                ))
        
        # Verificar conflitos de data de expiração
        service_expires = service_data.get("expires_at")
        subscription_due = subscription_data.get("next_due_date")
        
        if service_expires and subscription_due:
            service_date = self._parse_datetime_with_timezone(service_expires)
            subscription_date = self._parse_datetime_with_timezone(subscription_due)
            
            # Considerar conflito se diferença > 1 dia
            if abs((service_date - subscription_date).days) > 1:
                conflicts.append(SubscriptionConflict(
                    field_name="expiration_date",
                    affiliate_services_value=service_expires,
                    multi_agent_subscriptions_value=subscription_due,
                    recommended_resolution=f"Usar data da assinatura: {subscription_due}",
                    severity="low"
                ))
        
        return conflicts

    async def _resolve_conflicts(
        self, 
        affiliate_id: UUID, 
        conflicts: List[SubscriptionConflict], 
        config: SubscriptionSyncConfig,
        dry_run: bool = False
    ) -> List[str]:
        """Resolve conflitos automaticamente baseado na configuração."""
        actions = []
        
        for conflict in conflicts:
            if conflict.severity in ["critical", "high"]:
                # Conflitos críticos requerem intervenção manual
                actions.append(f"[MANUAL] Conflito crítico em {conflict.field_name} requer revisão manual")
                continue
            
            # Resolver automaticamente baseado na preferência
            if config.prefer_source == SubscriptionSource.MULTI_AGENT_SUBSCRIPTIONS:
                if not dry_run:
                    await self._update_affiliate_service_from_subscription(affiliate_id, conflict)
                actions.append(f"Resolvido {conflict.field_name}: usado valor da assinatura")
            else:
                if not dry_run:
                    await self._update_subscription_from_service(affiliate_id, conflict)
                actions.append(f"Resolvido {conflict.field_name}: usado valor do serviço")
        
        return actions

    async def _update_affiliate_service_from_subscription(self, affiliate_id: UUID, conflict: SubscriptionConflict):
        """Atualiza affiliate_services com valor da subscription."""
        try:
            update_data = {}
            
            if conflict.field_name == "status":
                # Mapear status de subscription para service
                subscription_status = conflict.multi_agent_subscriptions_value
                if subscription_status in ["active"]:
                    update_data["status"] = "active"
                elif subscription_status in ["canceled", "expired"]:
                    update_data["status"] = "inactive"
                elif subscription_status in ["overdue"]:
                    update_data["status"] = "inactive"  # Temporariamente inativo
            
            if update_data:
                self.supabase.table(self.services_table)\
                    .update(update_data)\
                    .eq("affiliate_id", str(affiliate_id))\
                    .eq("service_type", "agente_ia")\
                    .execute()
                
                logger.debug(f"✅ Atualizado affiliate_service para {affiliate_id}: {update_data}")
        
        except Exception as e:
            logger.error(f"💥 Erro ao atualizar affiliate_service: {str(e)}")

    async def _update_subscription_from_service(self, affiliate_id: UUID, conflict: SubscriptionConflict):
        """Atualiza multi_agent_subscriptions com valor do service."""
        # Implementação similar, mas atualizando a tabela de subscriptions
        logger.debug(f"🔄 Atualizaria subscription para {affiliate_id} (não implementado)")

    async def _create_missing_tenant(self, affiliate_id: UUID, subscription_data: Dict[str, Any]) -> str:
        """Cria tenant faltante para um afiliado."""
        try:
            tenant_data = TenantCreate(
                affiliate_id=affiliate_id,
                agent_name="BIA",
                agent_personality="Assistente inteligente para vendas"
            )
            
            tenant = self.tenant_service.create_tenant(tenant_data)
            logger.info(f"✅ Tenant criado para afiliado {affiliate_id}: {tenant.id}")
            
            return f"Criado tenant {tenant.id} para afiliado {affiliate_id}"
            
        except Exception as e:
            logger.error(f"💥 Erro ao criar tenant para {affiliate_id}: {str(e)}")
            return f"Erro ao criar tenant: {str(e)}"

    async def _check_affiliate_consistency(self, affiliate_id: UUID) -> List[Dict[str, Any]]:
        """Verifica consistência de dados de um afiliado."""
        inconsistencies = []
        
        try:
            service_data = await self._get_affiliate_service(affiliate_id)
            subscription_data = await self._get_multi_agent_subscription(affiliate_id)
            
            # Verificar se há dados em apenas uma tabela
            if service_data and not subscription_data:
                inconsistencies.append({
                    "type": "missing_subscription",
                    "description": "Tem serviço mas não tem assinatura"
                })
            
            if subscription_data and not service_data:
                inconsistencies.append({
                    "type": "missing_service", 
                    "description": "Tem assinatura mas não tem serviço"
                })
            
            # Verificar conflitos se ambos existem
            if service_data and subscription_data:
                conflicts = await self._identify_conflicts(service_data, subscription_data)
                for conflict in conflicts:
                    inconsistencies.append({
                        "type": "status_mismatch" if conflict.field_name == "status" else "date_conflict",
                        "description": f"Conflito em {conflict.field_name}: {conflict.affiliate_services_value} vs {conflict.multi_agent_subscriptions_value}"
                    })
        
        except Exception as e:
            logger.error(f"💥 Erro ao verificar consistência do afiliado {affiliate_id}: {str(e)}")
        
        return inconsistencies

    def _get_earliest_date(self, service_data: Optional[Dict], subscription_data: Optional[Dict], field: str) -> datetime:
        """Obtém a data mais antiga entre as duas fontes."""
        dates = []
        
        if service_data and service_data.get(field):
            dates.append(self._parse_datetime_with_timezone(service_data[field]))
        
        if subscription_data and subscription_data.get(field):
            dates.append(self._parse_datetime_with_timezone(subscription_data[field]))
        
        return min(dates) if dates else datetime.now(timezone.utc)

    def _get_latest_date(self, service_data: Optional[Dict], subscription_data: Optional[Dict], field: str) -> datetime:
        """Obtém a data mais recente entre as duas fontes."""
        dates = []
        
        if service_data and service_data.get(field):
            dates.append(self._parse_datetime_with_timezone(service_data[field]))
        
        if subscription_data and subscription_data.get(field):
            dates.append(self._parse_datetime_with_timezone(subscription_data[field]))
        
        return max(dates) if dates else datetime.now(timezone.utc)

    def _parse_datetime_with_timezone(self, date_str: str) -> datetime:
        """
        Parse datetime string garantindo timezone UTC.
        
        Args:
            date_str: String de data em formato ISO
            
        Returns:
            datetime: Objeto datetime com timezone UTC
        """
        if not date_str:
            return datetime.now(timezone.utc)
        
        try:
            # Se já tem timezone info, usar diretamente
            if date_str.endswith('Z'):
                # Substituir Z por +00:00 para ISO format
                date_str = date_str.replace('Z', '+00:00')
            elif '+' not in date_str and 'T' in date_str:
                # Se não tem timezone, assumir UTC
                if not date_str.endswith('+00:00'):
                    date_str += '+00:00'
            
            # Parse com timezone
            dt = datetime.fromisoformat(date_str)
            
            # Garantir que está em UTC
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            elif dt.tzinfo != timezone.utc:
                dt = dt.astimezone(timezone.utc)
            
            return dt
            
        except (ValueError, TypeError) as e:
            logger.warning(f"⚠️ Erro ao fazer parse de data '{date_str}': {str(e)}")
            return datetime.now(timezone.utc)