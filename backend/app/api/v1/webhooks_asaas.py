"""
Webhook handler para processar eventos do Asaas
Gerencia ciclo de vida de assinaturas do Agente IA
"""

from fastapi import APIRouter, Request
from app.db.supabase import get_supabase
from datetime import datetime, timedelta
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/asaas")
async def asaas_webhook(request: Request):
    """
    Processa webhooks do Asaas para ciclo de vida de assinaturas.
    
    Eventos suportados:
    - PAYMENT_CONFIRMED: Renovar assinatura por +30 dias
    - SUBSCRIPTION_DELETED: Cancelar tenant
    - PAYMENT_OVERDUE: Suspender temporariamente
    """
    try:
        payload = await request.json()
        event = payload.get("event")
        payment = payload.get("payment", {})
        subscription = payload.get("subscription", {})
        
        # Extrair subscription_id (pode vir de subscription.id ou payment.subscription)
        subscription_id = subscription.get("id") or payment.get("subscription")
        
        logger.info(f"Asaas webhook received: {event} | subscription_id: {subscription_id}")
        
        supabase = get_supabase()
        
        if event == "PAYMENT_CONFIRMED":
            # Renovar assinatura por +30 dias
            next_due = datetime.now() + timedelta(days=30)
            
            result = supabase.table("multi_agent_subscriptions")\
                .update({
                    "status": "active",
                    "next_due_date": next_due.strftime("%Y-%m-%d"),
                    "updated_at": datetime.now().isoformat()
                })\
                .eq("asaas_subscription_id", subscription_id)\
                .execute()
            
            # Garantir que tenant está ativo
            if result.data:
                tenant_id = result.data[0].get("tenant_id")
                supabase.table("multi_agent_tenants")\
                    .update({
                        "status": "active",
                        "suspended_at": None,
                        "updated_at": datetime.now().isoformat()
                    })\
                    .eq("id", tenant_id)\
                    .execute()
                logger.info(f"Subscription renewed: {subscription_id}")
            
        elif event == "SUBSCRIPTION_DELETED":
            # Cancelar tenant
            result = supabase.table("multi_agent_subscriptions")\
                .update({
                    "status": "canceled",
                    "canceled_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                })\
                .eq("asaas_subscription_id", subscription_id)\
                .execute()
            
            if result.data:
                tenant_id = result.data[0].get("tenant_id")
                supabase.table("multi_agent_tenants")\
                    .update({
                        "status": "canceled",
                        "suspended_at": datetime.now().isoformat()
                    })\
                    .eq("id", tenant_id)\
                    .execute()
                logger.info(f"Subscription canceled: {subscription_id}")
                    
        elif event == "PAYMENT_OVERDUE":
            # Suspender temporariamente
            result = supabase.table("multi_agent_subscriptions")\
                .update({
                    "status": "overdue",
                    "updated_at": datetime.now().isoformat()
                })\
                .eq("asaas_subscription_id", subscription_id)\
                .execute()
            
            if result.data:
                tenant_id = result.data[0].get("tenant_id")
                supabase.table("multi_agent_tenants")\
                    .update({
                        "status": "suspended",
                        "suspended_at": datetime.now().isoformat()
                    })\
                    .eq("id", tenant_id)\
                    .execute()
                logger.info(f"Subscription overdue: {subscription_id}")
        
        # Retornar 200 OK para evitar retries infinitos do Asaas
        return {"status": "received", "event": event}
        
    except Exception as e:
        logger.error(f"Error processing Asaas webhook: {e}")
        # Retornar 200 para evitar retries infinitos
        return {"status": "error", "message": str(e)}
