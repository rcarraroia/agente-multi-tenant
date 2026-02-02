from pydantic import BaseModel, UUID4, Field, ConfigDict
from typing import Optional
from datetime import datetime
from enum import Enum

class TenantStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CANCELED = "canceled"

class TenantBase(BaseModel):
    agent_name: str = "BIA"
    agent_personality: Optional[str] = None
    knowledge_enabled: bool = True
    whatsapp_number: Optional[str] = None
    evolution_instance_id: Optional[str] = None
    chatwoot_inbox_id: Optional[str] = None
    openai_api_key: Optional[str] = None

class TenantCreate(TenantBase):
    affiliate_id: UUID4

class TenantUpdate(BaseModel):
    status: Optional[TenantStatus] = None
    agent_name: Optional[str] = None
    agent_personality: Optional[str] = None
    knowledge_enabled: Optional[bool] = None
    whatsapp_number: Optional[str] = None
    evolution_instance_id: Optional[str] = None
    chatwoot_inbox_id: Optional[str] = None
    whatsapp_provider: Optional[str] = None
    whatsapp_config: Optional[dict] = None
    whatsapp_status: Optional[str] = None
    chatwoot_account_id: Optional[int] = None
    chatwoot_api_access_token: Optional[str] = None
    openai_api_key: Optional[str] = None

class Tenant(TenantBase):
    id: UUID4
    affiliate_id: UUID4
    status: TenantStatus
    created_at: datetime
    updated_at: datetime
    activated_at: Optional[datetime] = None
    suspended_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
