from uuid import UUID
from typing import Optional, List
from app.db.supabase import get_supabase
from app.schemas.conversation import ConversationCreate, ConversationUpdate, Conversation, ConversationStatus
from app.schemas.message import MessageCreate, Message
from app.core.exceptions import EntityNotFoundException
from postgrest.exceptions import APIError

class ConversationService:
    def __init__(self):
        self.supabase = get_supabase()
        self.conv_table = "multi_agent_conversations"
        self.msg_table = "multi_agent_messages"

    def get_or_create_conversation(self, tenant_id: UUID, phone: str, customer_name: Optional[str] = None) -> Conversation:
        # Try to find active conversation
        response = self.supabase.table(self.conv_table)\
            .select("*")\
            .eq("tenant_id", str(tenant_id))\
            .eq("customer_phone", phone)\
            .neq("status", ConversationStatus.CLOSED.value)\
            .execute()
        
        if response.data:
            return Conversation.model_validate(response.data[0])
        
        # Create new conversation
        new_conv = ConversationCreate(
            tenant_id=tenant_id,
            customer_phone=phone,
            customer_name=customer_name
        )
        # Note: Chatwoot ID is not passed here, handled in get_or_create_by_chatwoot_id
        
        create_res = self.supabase.table(self.conv_table)\
            .insert(new_conv.model_dump(mode='json'))\
            .execute()
            
        conv_data = create_res.data[0]
        
        # Atribuir funil padrão
        self._assign_to_default_funnel(tenant_id, conv_data["id"])
        
        # Recarregar conversa para garantir dados atualizados (funnel_id, stage_id)
        final_conv = self.supabase.table(self.conv_table)\
            .select("*")\
            .eq("id", conv_data["id"])\
            .single()\
            .execute()
            
        return Conversation.model_validate(final_conv.data)

    def get_or_create_by_chatwoot_id(self, tenant_id: UUID, chatwoot_conv_id: str, phone: Optional[str] = None, customer_name: Optional[str] = None) -> Conversation:
        # Try to find by chatwoot ID
        response = self.supabase.table(self.conv_table)\
            .select("*")\
            .eq("tenant_id", str(tenant_id))\
            .eq("chatwoot_conversation_id", str(chatwoot_conv_id))\
            .execute()
        
        if response.data:
            return Conversation.model_validate(response.data[0])
            
        # If not found by ID, try phone if provided (linking existing conversation)
        if phone:
            response = self.supabase.table(self.conv_table)\
                .select("*")\
                .eq("tenant_id", str(tenant_id))\
                .eq("customer_phone", phone)\
                .neq("status", ConversationStatus.CLOSED.value)\
                .execute()
                
            if response.data:
                # Link chatwoot ID to existing Conversation
                existing = response.data[0]
                self.supabase.table(self.conv_table)\
                    .update({"chatwoot_conversation_id": str(chatwoot_conv_id)})\
                    .eq("id", existing["id"])\
                    .execute()
                existing["chatwoot_conversation_id"] = str(chatwoot_conv_id)
                return Conversation.model_validate(existing)
        
        # Create new
        new_conv_data = {
            "tenant_id": str(tenant_id),
            "customer_phone": phone or "unknown",
            "customer_name": customer_name or "Unknown",
            "chatwoot_conversation_id": str(chatwoot_conv_id),
            "status": ConversationStatus.ACTIVE.value,
            "channel": "whatsapp"
        }
        
        create_res = self.supabase.table(self.conv_table)\
            .insert(new_conv_data)\
            .execute()
            
        conv_data = create_res.data[0]
        
        # Atribuir funil padrão
        self._assign_to_default_funnel(tenant_id, conv_data["id"])
        
        # Recarregar conversa
        final_conv = self.supabase.table(self.conv_table)\
            .select("*")\
            .eq("id", conv_data["id"])\
            .single()\
            .execute()
            
        return Conversation.model_validate(final_conv.data)

    def add_message(self, data: MessageCreate) -> Message:
        # Insert message
        response = self.supabase.table(self.msg_table)\
            .insert(data.model_dump(mode='json'))\
            .execute()
        
        message = Message.model_validate(response.data[0])
        
        # Update conversation timestamp
        self.supabase.table(self.conv_table)\
            .update({
                "last_message_at": "now()",
            })\
            .eq("id", str(data.conversation_id))\
            .execute()
            
        return message

    def list_conversations(self, tenant_id: UUID, status: Optional[ConversationStatus] = None, limit: int = 10) -> List[Conversation]:
        query = self.supabase.table(self.conv_table)\
            .select("*")\
            .eq("tenant_id", str(tenant_id))\
            .order("last_message_at", desc=True)\
            .limit(limit)
            
        if status:
            query = query.eq("status", status.value)
            
        response = query.execute()
        
        return [Conversation.model_validate(item) for item in response.data]

    def _assign_to_default_funnel(self, tenant_id: UUID, conversation_id: UUID):
        """Atribuir funil padrão e primeira etapa a uma nova conversa"""
        try:
            # 1. Buscar funil padrão
            funnel_res = self.supabase.table("crm_funnels")\
                .select("id")\
                .eq("tenant_id", str(tenant_id))\
                .eq("is_default", True)\
                .single()\
                .execute()
            
            if not funnel_res.data:
                return
            
            funnel_id = funnel_res.data["id"]
            
            # 2. Buscar primeira etapa
            stage_res = self.supabase.table("crm_stages")\
                .select("id")\
                .eq("funnel_id", funnel_id)\
                .order("position")\
                .limit(1)\
                .execute()
            
            if not stage_res.data:
                return
            
            stage_id = stage_res.data[0]["id"]
            
            # 3. Atualizar conversa
            self.supabase.table(self.conv_table)\
                .update({
                    "funnel_id": funnel_id,
                    "stage_id": stage_id
                })\
                .eq("id", str(conversation_id))\
                .execute()
            
            # 4. Criar histórico inicial
            self.supabase.table("crm_stage_history")\
                .insert({
                    "conversation_id": str(conversation_id),
                    "tenant_id": str(tenant_id),
                    "from_stage_id": None,
                    "to_stage_id": stage_id,
                    "notes": "Atribuição automática inicial"
                })\
                .execute()
        except Exception as e:
            print(f"Erro ao atribuir funil padrão à conversa {conversation_id}: {str(e)}")
