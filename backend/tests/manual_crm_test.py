
import asyncio
import uuid
from app.services.conversation_service import ConversationService
from app.services.tenant_service import TenantService
from app.schemas.tenant import TenantCreate

async def test_crm_automation():
    print("Iniciando teste de automação CRM...")
    
    tenant_service = TenantService()
    conv_service = ConversationService()
    
    # 1. Obter tenant existente (do migration)
    # Assumindo que existe 1 tenant pois crm_funnels count = 1
    # Se não, criar um dummy.
    
    # Vamos listar tenants
    tenants = tenant_service.supabase.table("multi_agent_tenants").select("id").limit(1).execute()
    
    if not tenants.data:
        print("Nenhum tenant encontrado. Criando um...")
        # Criar tenant
        new_tenant = TenantCreate(
            name="Tenant Teste Automacao",
            slug="tenant-teste-automacao",
            affiliate_id=uuid.uuid4(), # Mock ID
            chatwoot_account_id=99999
        )
        tenant = await tenant_service.create_tenant(new_tenant)
        tenant_id = tenant.id
        print(f"Tenant criado: {tenant_id}")
    else:
        tenant_id = tenants.data[0]["id"]
        print(f"Usando tenant existente: {tenant_id}")
        
    # 2. Criar nova conversa
    phone = f"551199999{uuid.uuid4().hex[:4]}" # Phone único
    print(f"Criando conversa para telefone: {phone}")
    
    conv = conv_service.get_or_create_conversation(tenant_id, phone, "Cliente Teste")
    
    print(f"Conversa criada: {conv.id}")
    print(f"Funnel ID: {conv.funnel_id}")
    print(f"Stage ID: {conv.stage_id}")
    
    if not conv.funnel_id or not conv.stage_id:
        print("ERRO: Conversa não foi atribuída a um funil/etapa!")
        return
        
    print("SUCESSO: Conversa atribuída ao funil padrão.")
    
    # 3. Verificar histórico
    hist = conv_service.supabase.table("crm_stage_history")\
        .select("*")\
        .eq("conversation_id", str(conv.id))\
        .execute()
        
    if hist.data:
        print(f"Histórico inicial criado: {len(hist.data)} registro(s)")
        print(f"Detalhes: {hist.data[0]}")
    else:
        print("ERRO: Histórico inicial não criado.")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_crm_automation())
