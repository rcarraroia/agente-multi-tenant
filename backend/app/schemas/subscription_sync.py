"""
Schemas para sincronização de assinaturas.

Define os modelos de dados para unificar informações entre
affiliate_services e multi_agent_subscriptions.
"""

from pydantic import BaseModel, UUID4, Field, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

class SubscriptionSource(str, Enum):
    """Fonte da informação de assinatura."""
    AFFILIATE_SERVICES = "affiliate_services"
    MULTI_AGENT_SUBSCRIPTIONS = "multi_agent_subscriptions"
    UNIFIED = "unified"

class UnifiedSubscriptionStatus(str, Enum):
    """Status unificado de assinatura."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    TRIAL = "trial"
    PENDING = "pending"
    OVERDUE = "overdue"
    CANCELED = "canceled"
    EXPIRED = "expired"

class SubscriptionConflict(BaseModel):
    """Representa um conflito entre fontes de dados."""
    field_name: str
    affiliate_services_value: Any
    multi_agent_subscriptions_value: Any
    recommended_resolution: str
    severity: str = Field(..., pattern="^(low|medium|high|critical)$")

class UnifiedSubscription(BaseModel):
    """Representação unificada de uma assinatura."""
    affiliate_id: UUID4
    tenant_id: Optional[UUID4] = None
    
    # Status unificado
    status: UnifiedSubscriptionStatus
    is_active: bool
    
    # Informações de serviço (affiliate_services)
    service_type: Optional[str] = None
    service_expires_at: Optional[datetime] = None
    service_metadata: Optional[Dict[str, Any]] = None
    
    # Informações de assinatura (multi_agent_subscriptions)
    asaas_subscription_id: Optional[str] = None
    asaas_customer_id: Optional[str] = None
    plan_value_cents: Optional[int] = None
    billing_type: Optional[str] = None
    next_due_date: Optional[datetime] = None
    
    # Metadados de sincronização
    primary_source: SubscriptionSource
    last_synced_at: datetime
    conflicts: List[SubscriptionConflict] = []
    sync_notes: Optional[str] = None
    
    # Timestamps
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class SubscriptionSyncResult(BaseModel):
    """Resultado de uma operação de sincronização."""
    total_processed: int
    successful_syncs: int
    conflicts_found: int
    errors_encountered: int
    
    # Detalhes
    synced_affiliates: List[UUID4] = []
    conflicted_affiliates: List[UUID4] = []
    error_affiliates: List[UUID4] = []
    
    # Resumo de conflitos
    conflict_summary: Dict[str, int] = {}
    
    # Tempo de execução
    execution_time_seconds: float
    started_at: datetime
    completed_at: datetime

class SubscriptionSyncConfig(BaseModel):
    """Configuração para sincronização."""
    resolve_conflicts_automatically: bool = True
    prefer_source: SubscriptionSource = SubscriptionSource.MULTI_AGENT_SUBSCRIPTIONS
    update_inactive_records: bool = True
    create_missing_tenants: bool = True
    dry_run: bool = False
    batch_size: int = 100
    
class SubscriptionValidationResult(BaseModel):
    """Resultado da validação de consistência."""
    is_consistent: bool
    total_checked: int
    inconsistencies_found: int
    
    # Tipos de inconsistências
    missing_in_services: List[UUID4] = []
    missing_in_subscriptions: List[UUID4] = []
    status_mismatches: List[UUID4] = []
    date_conflicts: List[UUID4] = []
    
    # Detalhes
    validation_errors: List[str] = []
    validation_warnings: List[str] = []
    
    validated_at: datetime

class SubscriptionMigrationPlan(BaseModel):
    """Plano de migração de dados."""
    total_records: int
    records_to_create: int
    records_to_update: int
    records_to_merge: int
    
    # Ações específicas
    create_tenants: List[UUID4] = []
    update_services: List[UUID4] = []
    merge_subscriptions: List[UUID4] = []
    
    # Estimativas
    estimated_duration_minutes: int
    requires_manual_review: List[UUID4] = []
    
    created_at: datetime