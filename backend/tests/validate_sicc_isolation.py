import asyncio
import uuid
import logging
import sys
import os

# Adicionar o path do backend para importar os módulos do app
sys.path.append(os.path.join(os.getcwd(), 'backend'))
os.environ["PYTHONPATH"] = os.path.join(os.getcwd(), 'backend')

from dotenv import load_dotenv

# Carregar explicitamente o .env do backend
load_dotenv('backend/.env')

from app.ai.sicc.sicc_service import SICCService
from app.db.supabase import get_supabase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def validate_isolation():
    logger.info("Iniciando Validação de Isolamento Multi-Tenant SICC 2.0...")
    
    sicc = SICCService()
    supabase = get_supabase()
    
    # 1. IDs de Teste
    # Tenant A (Existente ou Criado)
    tenant_a_id = uuid.UUID("20b8bef6-fa97-469b-bdef-eb95c9c0e223") 
    tenant_b_id = uuid.uuid4() # Um ID aleatório que não deve ver nada
    
    # Criar uma conversa fake para o Tenant A
    conv_id = uuid.uuid4()
    try:
        supabase.table("multi_agent_conversations").insert({
            "id": str(conv_id),
            "tenant_id": str(tenant_a_id),
            "customer_phone": "5511999999999",
            "status": "ai"
        }).execute()
        logger.info(f"Conversa de teste criada: {conv_id}")
    except Exception as e:
        logger.error(f"Erro ao criar conversa de teste: {e}")
        return

    try:
        # 2. Armazenar Memória para Tenant A
        secret_content = "O código secreto do Tenant A é 123456."
        logger.info(f"Armazenando memória para Tenant A...")
        await sicc.store_interaction(tenant_a_id, conv_id, secret_content)
        
        # Aguardar um pouco para garantir persistência (embora seja síncrono no script)
        await asyncio.sleep(1)

        # 3. Testar Busca para Tenant A
        logger.info("Testando busca para Tenant A (Deve encontrar)...")
        results_a = await sicc.memory.search(tenant_a_id, "Qual o código secreto?")
        
        found_a = any(secret_content in r.content for r in results_a)
        if found_a:
            logger.info("✅ SUCESSO: Tenant A encontrou sua própria memória.")
        else:
            logger.error("❌ FALHA: Tenant A NÃO encontrou sua própria memória.")

        # 4. Testar Busca para Tenant B (VULNERABILIDADE SE ENCONTRAR)
        logger.info("Testando busca para Tenant B (NÃO DEVE ENCONTRAR)...")
        results_b = await sicc.memory.search(tenant_b_id, "Qual o código secreto?")
        
        found_b = any(secret_content in r.content for r in results_b)
        if not found_b and len(results_b) == 0:
            logger.info("✅ SUCESSO: Tenant B está isolado e não viu os dados do Tenant A.")
        else:
            logger.error("❌ FALHA CRÍTICA: Tenant B acessou dados do Tenant A!")

    finally:
        # Cleanup
        logger.info("Limpando dados de teste...")
        supabase.table("sicc_memory_chunks").delete().eq("conversation_id", str(conv_id)).execute()
        supabase.table("multi_agent_conversations").delete().eq("id", str(conv_id)).execute()
        logger.info("Cleanup concluído.")

if __name__ == "__main__":
    asyncio.run(validate_isolation())
