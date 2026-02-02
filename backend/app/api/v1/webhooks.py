from fastapi import APIRouter, Depends, HTTPException, Request
from app.services.tenant_service import TenantService
from app.services.conversation_service import ConversationService
from app.services.chatwoot_service import ChatwootService
from app.services.whatsapp.providers.evolution import EvolutionProvider
from app.ai.agent import AgentService 
from app.schemas.tenant import TenantUpdate
import os
import json

router = APIRouter()

# Dependency for provider
def get_whatsapp_provider():
    api_url = os.getenv("EVOLUTION_API_URL")
    api_key = os.getenv("EVOLUTION_API_KEY")
    if not api_url or not api_key:
        raise HTTPException(status_code=500, detail="Evolution API not configured")
    return EvolutionProvider(api_url=api_url, api_key=api_key)

def get_chatwoot_service():
    return ChatwootService()

@router.post("/providers/evolution")
async def evolution_webhook(
    request: Request,
    provider: EvolutionProvider = Depends(get_whatsapp_provider),
    tenant_service: TenantService = Depends()
):
    payload = await request.json()
    event = await provider.parse_webhook(payload)
    
    if not event:
        return {"status": "ignored"}

    if event.event_type == "qrcode_updated":
         # Logic to save QR code would go here
         # For MVP, we rely on on-demand fetching via /whatsapp/qrcode endpoint
         pass

    elif event.event_type == "connection_update":
        # Logic to update tenant status would go here
        # Requires finding tenant by instance_id
        pass

    return {"status": "processed"}

@router.post("/chatwoot")
async def chatwoot_webhook(
    request: Request,
    tenant_service: TenantService = Depends(),
    conversation_service: ConversationService = Depends(),
    chatwoot_service: ChatwootService = Depends(get_chatwoot_service)
):
    try:
        payload = await request.json()
        event_type = payload.get("event")
        
        if event_type == "message_created":
            message_type = payload.get("message_type")
            is_private = payload.get("private", False)
            
            # Only process incoming public messages
            if message_type == "incoming" and not is_private:
                account_id = payload.get("account", {}).get("id")
                conversation_data = payload.get("conversation", {})
                chatwoot_conv_id = conversation_data.get("id")
                content = payload.get("content")
                sender = payload.get("sender", {})
                phone = sender.get("phone_number")
                name = sender.get("name")
                
                # 1. Identify Tenant
                try:
                    tenant = tenant_service.get_by_chatwoot_account_id(account_id)
                except Exception as e:
                    print(f"Tenant not found for account {account_id}: {e}")
                    return {"status": "ignored", "reason": "tenant_not_found"}

                # 2. Check Conversation Status (Handoff Logic)
                # Chatwoot status: open, resolved, pending, snoozed
                cw_status = conversation_data.get("status")
                
                # If status is Open, it's human handled. Ignore.
                if cw_status == "open":
                    return {"status": "ignored", "reason": "human_handling"}
                
                # 3. Get Internal Conversation
                conv = conversation_service.get_or_create_by_chatwoot_id(
                    tenant_id=tenant.id,
                    chatwoot_conv_id=str(chatwoot_conv_id),
                    phone=phone,
                    customer_name=name
                )
                
                # 4. Invoke AI Agent
                agent = AgentService() # Singleton
                result = await agent.process_message(conv.id, tenant.id, content)
                
                response_text = result.get("response")
                should_handoff = result.get("should_handoff")
                
                # 5. Send Response
                if response_text:
                    await chatwoot_service.send_message(account_id, chatwoot_conv_id, response_text)
                
                # 6. Handle Handoff
                if should_handoff:
                    await chatwoot_service.toggle_status(account_id, chatwoot_conv_id, "open")
                    # Optionally notify agent?
        
        elif event_type == "conversation_status_changed":
            # Can be used to sync internal status or log metrics
            pass
            
        return {"status": "received"}
        
    except Exception as e:
        print(f"Error processing webhook: {e}")
        # Return 200 to avoid Chatwoot retrying endlessly on internal logic bugs
        return {"status": "error", "message": str(e)}
