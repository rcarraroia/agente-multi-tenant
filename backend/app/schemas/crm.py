from pydantic import BaseModel, UUID4, Field, ConfigDict, field_validator
from typing import Optional, List
from datetime import datetime
import re

# ============ FUNNELS ============

class FunnelBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)

class FunnelCreate(FunnelBase):
    pass

class FunnelUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None

class Funnel(FunnelBase):
    id: UUID4
    tenant_id: UUID4
    is_default: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class FunnelWithStages(Funnel):
    stages: List['Stage'] = []

# ============ STAGES ============

class StageBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    position: int = Field(..., gt=0)
    color: str = Field(default='#3B82F6', pattern=r'^#[0-9A-Fa-f]{6}$')
    
    @field_validator('color')
    @classmethod
    def validate_color(cls, v: str) -> str:
        if not re.match(r'^#[0-9A-Fa-f]{6}$', v):
            raise ValueError('Color must be a valid hex color (#RRGGBB)')
        return v.upper()

class StageCreate(StageBase):
    funnel_id: UUID4

class StageUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')

class Stage(StageBase):
    id: UUID4
    funnel_id: UUID4
    tenant_id: UUID4
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class StageReorderItem(BaseModel):
    id: UUID4
    position: int = Field(..., gt=0)

# ============ STAGE HISTORY ============

class StageHistoryBase(BaseModel):
    notes: Optional[str] = Field(None, max_length=500)

class StageHistoryCreate(StageHistoryBase):
    conversation_id: UUID4
    tenant_id: UUID4
    from_stage_id: Optional[UUID4] = None
    to_stage_id: UUID4
    moved_by: Optional[UUID4] = None

class StageHistory(StageHistoryBase):
    id: UUID4
    conversation_id: UUID4
    tenant_id: UUID4
    from_stage_id: Optional[UUID4]
    to_stage_id: UUID4
    moved_by: Optional[UUID4]
    moved_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class StageHistoryWithDetails(StageHistory):
    from_stage: Optional[Stage] = None
    to_stage: Stage
    moved_by_name: Optional[str] = None

# ============ MOVE CONVERSATION ============

class MoveConversationRequest(BaseModel):
    to_stage_id: UUID4
    notes: Optional[str] = Field(None, max_length=500)

# Import forward references
from app.schemas.crm import Stage
FunnelWithStages.model_rebuild()
