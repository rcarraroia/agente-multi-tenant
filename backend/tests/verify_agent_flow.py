import sys
import os
import asyncio
from uuid import uuid4
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import app.db.supabase as supabase_module
import app.ai.memory as memory_module

# MOCK INFRASTRUCTURE (Supabase & Redis)
def mock_get_supabase():
    class MockSupabase:
        def table(self, name): return self
        def insert(self, data): return self
        def update(self, data): return self
        def eq(self, col, val): return self
        def execute(self): return type('obj', (object,), {'data': []})
        def rpc(self, name, params): return self
    return MockSupabase()

def mock_redis_from_url(url, decode_responses=True):
    class MockRedis:
        def pipeline(self): return self
        def rpush(self, key, val): return self
        def lrange(self, key, s, e): return []
        def expire(self, key, ttl): return self
        def ltrim(self, key, s, e): return self
        def execute(self): return self
    return MockRedis()

# Apply Mocks BEFORE importing dependent modules
supabase_module.get_supabase = mock_get_supabase
memory_module.redis.from_url = mock_redis_from_url

# NOW Import modules that use the mocked functions
from app.ai.agent import AgentService
from app.ai.knowledge import KnowledgeService
from app.ai.memory import RedisMemoryManager
from app.schemas.tenant import Tenant
from app.services.tenant_service import TenantService
import app.ai.nodes as nodes_module # Helper to patch llm
from langchain_core.runnables import Runnable

from langchain_core.messages import AIMessage

# MOCK LLM to avoid 401 Error
class MockLLM(Runnable):
    def bind(self, **kwargs): return self # Handle .bind() call
    
    def invoke(self, input, config=None, **kwargs):
        # Sync version (not used but good for Runnable completeness)
        import asyncio
        return asyncio.run(self.ainvoke(input, config, **kwargs))

    async def ainvoke(self, input, config=None, **kwargs):
        # input can be dict (chain) or list of messages (direct invoke)
        # We infer type of prompt based on content
        
        # 1. Intent Classification
        # Input is dict with 'history' and 'message' usually processed by chain
        # But here 'chain' is prompt | llm | parser.
        # LangChain chain invokes llm with Formatted Prompt (String or Messages).
        
        # Start simple: Inspect the input if possible, or context.
        # Since I can't easily inspect the 'prompt' object in chain logic without deep mocks,
        # I will rely on the fact that 'nodes.py' uses specific chains.
        
        # BUT: nodes.py defines `chain = prompt | llm | StrOutputParser`.
        # When chain.ainvoke is called, LLM receives `ChatPromptValue` or list of messages.
        
        # Let's try to match content.
        text_input = str(input)
        
        if "categories:" in text_input or "Classifique" in text_input:
            if "Oi" in text_input or "Olá" in text_input: return AIMessage(content="GREETING")
            if "colchão" in text_input: return AIMessage(content="QUESTION")
            if "atendente" in text_input: return AIMessage(content="HANDOFF")
            return AIMessage(content="OTHER")
            
        elif "Avalie a resposta" in text_input:
             # Handoff Eval
             if "quero falar" in text_input.lower() or "atendente" in text_input.lower():
                 return AIMessage(content='{"should_handoff": true, "reason": "User request"}')
             return AIMessage(content='{"should_handoff": false}')
             
        else:
            # Generation
            return AIMessage(content="Resposta simulada do BIA sobre colchões.")

nodes_module.llm = MockLLM()

# Mocks for Logic
async def mock_search_relevant(self, query, tenant_id, top_k=3):
    print(f"   [MOCK RAG] Searching for: {query}")
    if "colchão" in query.lower():
        return "Os colchões magnéticos da Slim Quality possuem 300 imãs e infravermelho longo."
    return ""

def mock_get_history(self, conversation_id):
    return []

def mock_add_message(self, conversation_id, role, content):
    print(f"   [MOCK REDIS] Saving {role}: {content}")

def mock_get_tenant(self, tenant_id):
    class MockTenant:
        agent_name = "BIA Teste"
        agent_personality = "Prestativa"
    return MockTenant()

def mock_register_handoff(self, conv, tenant, reason):
    print(f"   [MOCK HANDOFF] Registered: {reason}")

# Monkey Patch
KnowledgeService.search_relevant = mock_search_relevant
RedisMemoryManager.get_history = mock_get_history
RedisMemoryManager.add_message = mock_add_message
TenantService.get_by_id = mock_get_tenant
AgentService._register_handoff = mock_register_handoff

async def test_agent_flow():
    print("\n--- AGENT AI FLOW TEST ---")
    agent = AgentService()
    
    conv_id = uuid4()
    tenant_id = uuid4()

    # Scenario 1: Greeting
    print("\n1. User: Oi, tudo bem?")
    res = await agent.process_message(conv_id, tenant_id, "Oi, tudo bem?")
    print(f"   Intent: {res['intent']}")
    print(f"   Response: {res['response']}")
    
    # Scenario 2: Question (RAG)
    print("\n2. User: Como funciona o colchão magnético?")
    res = await agent.process_message(conv_id, tenant_id, "Como funciona o colchão magnético?")
    print(f"   Intent: {res['intent']}")
    print(f"   Response: {res['response']}")

    # Scenario 3: Handoff
    print("\n3. User: Quero falar com um atendente agora!")
    res = await agent.process_message(conv_id, tenant_id, "Quero falar com um atendente agora!")
    print(f"   Intent: {res['intent']}")
    print(f"   Response: {res['response']}")
    print(f"   Handoff: {res['should_handoff']}")

if __name__ == "__main__":
    asyncio.run(test_agent_flow())
