import sys
import os
from uuid import uuid4, UUID
from datetime import datetime
from fastapi.testclient import TestClient

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app
from app.api import deps
from app.schemas.tenant import Tenant, TenantStatus
from app.schemas.conversation import Conversation, ConversationStatus
from app.services.tenant_service import TenantService
from app.services.conversation_service import ConversationService

# Mocks
MOCK_AFFILIATE_ID = uuid4()
MOCK_TENANT_ID = uuid4()
MOCK_USER_ID = "user_123"

mock_tenant = Tenant(
    id=MOCK_TENANT_ID,
    affiliate_id=MOCK_AFFILIATE_ID,
    status=TenantStatus.ACTIVE,
    created_at=datetime.now(),
    updated_at=datetime.now(),
    agent_name="BIA - Teste",
    knowledge_enabled=True
)

# Override Dependencies
async def override_get_current_user_id():
    return MOCK_USER_ID

async def override_get_current_affiliate_id():
    return MOCK_AFFILIATE_ID

async def override_get_current_tenant():
    return mock_tenant

# Mock Services
class MockTenantService:
    def create_tenant(self, data):
        return mock_tenant
    def update_tenant(self, id, data):
        return mock_tenant

class MockConversationService:
    def list_conversations(self, tenant_id, status=None, limit=10):
        return [
            Conversation(
                id=uuid4(),
                tenant_id=tenant_id,
                channel="whatsapp",
                customer_phone="5511999999999",
                status=ConversationStatus.AI,
                unread_count=0,
                last_message_at=datetime.now(),
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
        ]

app.dependency_overrides[deps.get_current_user_id] = override_get_current_user_id
app.dependency_overrides[deps.get_current_affiliate_id] = override_get_current_affiliate_id
app.dependency_overrides[deps.get_current_tenant] = override_get_current_tenant
app.dependency_overrides[TenantService] = MockTenantService
app.dependency_overrides[ConversationService] = MockConversationService

client = TestClient(app)

def test_api():
    print("\n--- API ENDPOINTS TEST ---")
    
    # 1. Test Tenant Me
    print("\n1. GET /api/v1/tenants/me")
    resp = client.get("/api/v1/tenants/me")
    print(f"Status: {resp.status_code}")
    print(f"Body: {resp.json()}")
    assert resp.status_code == 200
    assert resp.json()['data']['id'] == str(MOCK_TENANT_ID)

    # 2. Test Conversations List
    print("\n2. GET /api/v1/conversations/")
    resp = client.get("/api/v1/conversations/")
    print(f"Status: {resp.status_code}")
    # print(f"Body: {resp.json()}")
    assert resp.status_code == 200
    assert len(resp.json()['data']) > 0
    assert resp.json()['data'][0]['tenant_id'] == str(MOCK_TENANT_ID)

    print("\n✅ API Validation Successful!")

if __name__ == "__main__":
    test_api()
