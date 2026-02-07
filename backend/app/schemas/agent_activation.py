"""
Schemas para ativação de agentes.

Define os modelos de dados para o processo de ativação de agentes,
incluindo validação de assinaturas e status de ativação.
"""

from pydantic import BaseModel, UUID4, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

class ActivationStatus(str, Enum):
    """Status possíveis para ativação de agente."""
    PENDING = "pending"           # Aguardando validação
    ACTIVE = "active"            # Ativo e funcionando
    SUSPENDED = "suspended"      # Suspenso temporariamente
    EXPIRED = "expired"          # Assinatura expirada
    FAILED = "failed"            # Falha na ativação
    CANCELED = "canceled"        # Cancelado pelo usuário

class AgentActivationBase(BaseModel):
    """Base para ativação de agente."""
    affiliate_id: UUID4
    agent_name: str = Field(..., min_length=3, max_length=100)
    agent_personality: Optional[str] = Field(None, max_length=500)
    activation_reason: Optional[str] = Field(None, max_length=200)

class AgentActivationCreate(AgentActivationBase):
    """Dados para criar nova ativação de agente."""
    subscription_id: Optional[str] = None  # ID da assinatura no Asaas
    metadata: Optional[Dict[str, Any]] = None

class AgentActivationUpdate(BaseModel):
    """Dados para atualizar ativação de agente."""
    status: Optional[ActivationStatus] = None
    agent_name: Optional[str] = Field(None, min_length=3, max_length=100)
    agent_personality: Optional[str] = Field(None, max_length=500)
    deactivation_reason: Optional[str] = Field(None, max_length=200)
    metadata: Optional[Dict[str, Any]] = None

class AgentActivation(AgentActivationBase):
    """Ativação de agente completa."""
    id: UUID4
    tenant_id: UUID4
    status: ActivationStatus
    subscription_id: Optional[str] = None
    subscription_valid: bool = False
    subscription_expires_at: Optional[datetime] = None
    activated_at: Optional[datetime] = None
    deactivated_at: Optional[datetime] = None
    last_validated_at: Optional[datetime] = None
    deactivation_reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ActivationValidationResult(BaseModel):
    """Resultado da validação de ativação."""
    is_valid: bool
    status: ActivationStatus
    affiliate_id: UUID4
    tenant_id: Optional[UUID4] = None
    subscription_valid: bool = False
    subscription_expires_at: Optional[datetime] = None
    validation_errors: list[str] = []
    validation_warnings: list[str] = []
    last_validated_at: datetime

class ActivationSummary(BaseModel):
    """Resumo de ativação para dashboards."""
    total_activations: int
    active_count: int
    suspended_count: int
    expired_count: int
    pending_count: int
    failed_count: int
    canceled_count: int
    activation_rate: float  # Percentual de ativações bem-sucedidas
    
class AffiliateActivationStatus(BaseModel):
    """Status de ativação específico de um afiliado."""
    affiliate_id: UUID4
    has_active_agent: bool
    agent_name: Optional[str] = None
    agent_personality: Optional[str] = None
    status: Optional[ActivationStatus] = None
    activated_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    tenant_id: Optional[UUID4] = None
    subscription_valid: bool = False
    days_until_expiration: Optional[int] = None
    can_reactivate: bool = True
    reactivation_blocked_reason: Optional[str] = None