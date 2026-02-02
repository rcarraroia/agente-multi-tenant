import sys
import os
from uuid import uuid4
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.schemas.tenant import TenantCreate
from app.schemas.conversation import Conversation
from app.schemas.message import MessageCreate, MessageDirection, SenderType, ContentType
from app.services.tenant_service import TenantService
from app.services.conversation_service import ConversationService

def test_services():
    print("\n--- TEST: TenantService ---")
    tenant_service = TenantService()
    
    # 1. Create Tenant (Mock Affiliate ID)
    affiliate_id = uuid4()
    print(f"Creating tenant for affiliate {affiliate_id}")
    
    tenant_data = TenantCreate(
        affiliate_id=affiliate_id,
        agent_name="BIA - Teste",
        whatsapp_number="5511999999999"
    )
    
    try:
        tenant = tenant_service.create_tenant(tenant_data)
        print(f"✅ Created Tenant: {tenant.id} | Status: {tenant.status}")
    except Exception as e:
        print(f"❌ Error creating tenant: {e}")
        return

    print("\n--- TEST: ConversationService ---")
    conv_service = ConversationService()
    
    # 2. Create Conversation
    phone = "5511888888888"
    print(f"Starting conversation for {phone} on Tenant {tenant.id}")
    
    try:
        conv = conv_service.get_or_create_conversation(tenant.id, phone, "Cliente Teste")
        print(f"✅ Conversation Active: {conv.id} | Status: {conv.status}")
    except Exception as e:
        print(f"❌ Error creating conversation: {e}")
        return

    # 3. Add Message
    msg_data = MessageCreate(
        conversation_id=conv.id,
        tenant_id=tenant.id,
        direction=MessageDirection.INCOMING,
        sender_type=SenderType.CUSTOMER,
        content_type=ContentType.TEXT,
        content_text="Olá, gostaria de saber mais sobre o produto.",
        whatsapp_message_id=f"wamid.{uuid4()}"
    )
    
    try:
        msg = conv_service.add_message(msg_data)
        print(f"✅ Message Added: {msg.id} | Content: {msg.content_text}")
    except Exception as e:
        print(f"❌ Error adding message: {e}")

if __name__ == "__main__":
    test_services()
