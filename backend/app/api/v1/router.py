from fastapi import APIRouter
from app.api.v1 import tenants, conversations, webhooks, whatsapp, webhooks_asaas, crm, knowledge

api_router = APIRouter()

api_router.include_router(tenants.router, prefix="/tenants", tags=["tenants"])
api_router.include_router(conversations.router, prefix="/conversations", tags=["conversations"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
api_router.include_router(webhooks_asaas.router, prefix="/webhooks", tags=["webhooks"])
api_router.include_router(whatsapp.router, prefix="/whatsapp", tags=["whatsapp"])
api_router.include_router(crm.router, prefix="/crm", tags=["crm"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
