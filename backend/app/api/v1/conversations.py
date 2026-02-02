from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import UUID4

from app.api import deps
from app.schemas.conversation import Conversation, ConversationStatus
from app.schemas.message import Message, MessageCreate, MessageCreatePayload
from app.services.conversation_service import ConversationService
from app.schemas.tenant import Tenant
from app.api.deps import APIResponse
from app.schemas.common import PaginatedResponse

router = APIRouter()

@router.get("/", response_model=APIResponse)
def list_conversations(
    *,
    tenant: Tenant = Depends(deps.get_current_tenant),
    status: Optional[ConversationStatus] = None,
    limit: int = Query(10, gt=0, le=100),
    service: ConversationService = Depends(ConversationService)
) -> Any:
    """
    List conversations for the current tenant.
    """
    conversations = service.list_conversations(tenant.id, status=status, limit=limit)
    # Simple pagination wrapper (TODO: implement full pagination in service)
    # Since service returns List[Conversation] directly now:
    return APIResponse(data=conversations)

@router.get("/{conversation_id}", response_model=APIResponse)
def read_conversation(
    *,
    conversation_id: UUID4,
    tenant: Tenant = Depends(deps.get_current_tenant),
    service: ConversationService = Depends(ConversationService)
) -> Any:
    """
    Get conversation details.
    Validates if conversation belongs to tenant implicitly via RLS in service logic,
    but here we can rely on RLS/Service to return empty/error if not found.
    """
    # Ideally service should have get_by_id checking tenant_id
    # Current service definition doesn't have get_by_id, so let's use list or add it.
    # For now, let's trust RLS or add a specific get method in V2.
    # Direct access via Supabase with RLS context would be safer, 
    # but since we act as Service Role in backend, we MUST filter by tenant_id explicitly.
    
    # Quick fix implementation in router or service? 
    # Let's interact with service to fetch and check.
    # Extending service capability ad-hoc for Phase 1.
    
    # Re-using list for single item (inefficient but safe for now)
    # OR better: Add `get_conversation` to service. 
    # Assuming service extension or direct query here. 
    # Let's do direct query via deps helper style for simplicity? 
    # No, Service pattern. Let's use list and filter in code if needed or just fetch.
    
    # ACTUALLY, let's implement a clean check.
    # Service doesn't have `get_by_id` exposed in interface provided in walkthrough,
    # but `get_or_create` works by phone. We need by ID.
    
    # Implementation decision: Add ad-hoc logic using service's supabase client here
    # to avoid modifying service file if not strictly necessary, 
    # OR assume service has it. Let's assume we can fetch it.
    
    # Getting direct access to verify isolation:
    res = service.supabase.table("multi_agent_conversations")\
        .select("*")\
        .eq("id", str(conversation_id))\
        .eq("tenant_id", str(tenant.id))\
        .execute()
        
    if not res.data:
        raise HTTPException(status_code=404, detail="Conversation not found")
        
    return APIResponse(data=Conversation.model_validate(res.data[0]))

@router.get("/{conversation_id}/messages", response_model=APIResponse)
def list_messages(
    *,
    conversation_id: UUID4,
    tenant: Tenant = Depends(deps.get_current_tenant),
    service: ConversationService = Depends(ConversationService)
) -> Any:
    """
    List messages for a conversation.
    """
    # Security check: conversation belongs to tenant
    res_conv = service.supabase.table("multi_agent_conversations")\
        .select("id")\
        .eq("id", str(conversation_id))\
        .eq("tenant_id", str(tenant.id))\
        .execute()
        
    if not res_conv.data:
        raise HTTPException(status_code=404, detail="Conversation not found")
        
    # Fetch messages
    res_msgs = service.supabase.table("multi_agent_messages")\
        .select("*")\
        .eq("conversation_id", str(conversation_id))\
        .order("created_at", desc=False)\
        .execute()
        
    messages = [Message.model_validate(m) for m in res_msgs.data]
    return APIResponse(data=messages)

@router.post("/{conversation_id}/messages", response_model=APIResponse)
def create_message(
    *,
    conversation_id: UUID4,
    message_in: MessageCreatePayload,
    tenant: Tenant = Depends(deps.get_current_tenant),
    service: ConversationService = Depends(ConversationService)
) -> Any:
    """
    Send a message.
    """
    # Force tenant_id and match conv_id from path
    if str(message_in.conversation_id) != str(conversation_id):
        raise HTTPException(status_code=400, detail="Conversation ID mismatch")
    
    # Create full service DTO with injected tenant_id
    service_dto = MessageCreate(
        **message_in.model_dump(),
        tenant_id=tenant.id
    )
    
    try:
        message = service.add_message(service_dto)
        return APIResponse(data=message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
