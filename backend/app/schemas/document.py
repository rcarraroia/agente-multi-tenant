from datetime import datetime
from typing import Optional
from pydantic import BaseModel, UUID4

class DocumentBase(BaseModel):
    name: str
    file_path: str
    content_type: str
    size_bytes: int

class DocumentCreate(DocumentBase):
    tenant_id: UUID4

class Document(DocumentBase):
    id: UUID4
    tenant_id: UUID4
    status: str  # 'pending', 'processing', 'completed', 'failed'
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
