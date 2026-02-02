from pydantic import BaseModel, UUID4, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

class MessageDirection(str, Enum):
    INCOMING = "incoming"
    OUTGOING = "outgoing"

class SenderType(str, Enum):
    CUSTOMER = "customer"
    AI = "ai"
    HUMAN = "human"

class ContentType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"

class MessageBase(BaseModel):
    direction: MessageDirection
    sender_type: SenderType
    content_type: ContentType
    content_text: Optional[str] = None
    media_url: Optional[str] = None
    media_mime_type: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    whatsapp_message_id: Optional[str] = None

class MessageCreate(MessageBase):
    conversation_id: UUID4
    tenant_id: UUID4

class MessageCreatePayload(MessageBase):
    """Payload recebido na API (sem tenant_id, pois é injetado)"""
    conversation_id: UUID4

class Message(MessageBase):
    id: UUID4
    conversation_id: UUID4
    tenant_id: UUID4
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
