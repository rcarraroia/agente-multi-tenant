from uuid import UUID
from typing import Optional, Dict, Any

# Temporary simplified version without LangChain dependencies
class HumanMessage:
    def __init__(self, content: str):
        self.content = content

from app.services.tenant_service import TenantService
from app.db.supabase import get_supabase

class AgentService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AgentService, cls).__new__(cls)
            cls._instance.tenant_service = TenantService()
            cls._instance.supabase = get_supabase()
        return cls._instance

    async def process_message(
        self, 
        conversation_id: UUID,
        tenant_id: UUID,
        message_text: str
    ) -> Dict[str, Any]:
        """
        Simplified version without AI processing.
        Returns a basic response until AI dependencies are restored.
        """
        # 1. Fetch Tenant Config
        tenant = self.tenant_service.get_by_id(tenant_id)
        
        # 2. Simple response (placeholder until AI is restored)
        response_text = f"Olá! Sou o {tenant.agent_name if tenant else 'assistente'}. Recebi sua mensagem: '{message_text}'. O sistema de IA está sendo configurado."
        
        # 3. Basic response structure
        return {
            "response": response_text,
            "should_handoff": False,
            "intent": "greeting"
        }

    def _register_handoff(self, conversation_id: UUID, tenant_id: UUID, reason: str):
        try:
            # Insert into multi_agent_handoffs
            self.supabase.table("multi_agent_handoffs").insert({
                "conversation_id": str(conversation_id),
                "tenant_id": str(tenant_id),
                "reason": reason or "Auto-detected",
                "status": "pending"
            }).execute()
            
            # Update conversation status
            self.supabase.table("multi_agent_conversations").update({
                "status": "human",
                "assigned_to_user_id": None # Logic to assign logic could go here
            }).eq("id", str(conversation_id)).execute()
            
        except Exception as e:
            print(f"Handoff Registration Error: {e}")
