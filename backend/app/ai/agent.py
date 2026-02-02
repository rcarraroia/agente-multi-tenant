from uuid import UUID
from typing import Optional, Dict, Any
from langchain_core.messages import HumanMessage

from app.ai.graph import build_agent_graph
from app.ai.memory import RedisMemoryManager
from app.services.tenant_service import TenantService
from app.db.supabase import get_supabase

class AgentService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AgentService, cls).__new__(cls)
            cls._instance.graph = build_agent_graph()
            cls._instance.memory = RedisMemoryManager()
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
        Main entry point for processing messages.
        """
        # 1. Fetch Tenant Config (to pass personalization)
        tenant = self.tenant_service.get_by_id(tenant_id)
        tenant_config = {
            "agent_name": tenant.agent_name,
            "agent_personality": tenant.agent_personality
        }

        # 2. Invoke Graph
        initial_state = {
            "conversation_id": str(conversation_id),
            "tenant_id": str(tenant_id),
            "tenant_config": tenant_config,
            "messages": [HumanMessage(content=message_text)],
            "knowledge_context": "",
            "intent": "",
            "final_response": "",
            "should_handoff": False,
            "handoff_reason": None
        }

        result = await self.graph.ainvoke(initial_state)
        
        response_text = result.get("final_response", "")
        should_handoff = result.get("should_handoff", False)
        handoff_reason = result.get("handoff_reason")

        # 3. Persist Memory (User input + AI Response)
        self.memory.add_message(conversation_id, "user", message_text)
        if response_text:
            self.memory.add_message(conversation_id, "assistant", response_text)

        # 4. Handle Handoff Persistence
        if should_handoff:
            self._register_handoff(conversation_id, tenant_id, handoff_reason)

        return {
            "response": response_text,
            "should_handoff": should_handoff,
            "intent": result.get("intent")
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
