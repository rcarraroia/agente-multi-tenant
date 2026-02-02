from pydantic import BaseModel, UUID4, Field, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

# Enums
class ConversationStatus(str, Enum):
    AI = "ai"
    HUMAN = "human"
    CLOSED = "closed"

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

# Messages
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

class Message(MessageBase):
    id: UUID4
    conversation_id: UUID4
    tenant_id: UUID4
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# Conversations
class ConversationBase(BaseModel):
    channel: str = "whatsapp"
    customer_phone: str
    customer_name: Optional[str] = None

class ConversationCreate(ConversationBase):
    tenant_id: UUID4

class ConversationUpdate(BaseModel):
    status: Optional[ConversationStatus] = None
    unread_count: Optional[int] = None
    assigned_to_user_id: Optional[UUID4] = None

class Conversation(ConversationBase):
    id: UUID4
    tenant_id: UUID4
    status: ConversationStatus
    assigned_to_user_id: Optional[UUID4] = None
    funnel_id: Optional[UUID4] = None
    stage_id: Optional[UUID4] = None
    last_message_at: datetime
    unread_count: int
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
