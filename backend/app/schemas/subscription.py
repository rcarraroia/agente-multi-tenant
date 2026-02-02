from pydantic import BaseModel, UUID4, ConfigDict, Field
from typing import Optional
from datetime import datetime, date
from enum import Enum

class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    OVERDUE = "overdue"
    CANCELED = "canceled"
    EXPIRED = "expired"

class BillingType(str, Enum):
    CREDIT_CARD = "CREDIT_CARD"
    BOLETO = "BOLETO"
    PIX = "PIX"

class SubscriptionBase(BaseModel):
    asaas_subscription_id: str
    asaas_customer_id: str
    status: SubscriptionStatus
    plan_value_cents: int
    billing_type: BillingType
    next_due_date: Optional[date] = None

class Subscription(SubscriptionBase):
    id: UUID4
    tenant_id: UUID4
    affiliate_id: UUID4
    created_at: datetime
    updated_at: datetime
    canceled_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
