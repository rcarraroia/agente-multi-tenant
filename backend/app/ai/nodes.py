from typing import TypedDict, List, Optional, Any, Dict
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import json

from app.config import settings
from app.ai.knowledge import KnowledgeService
from app.ai.memory import RedisMemoryManager
from app.ai import prompts
from app.schemas.tenant import Tenant

# Define State Schema
class AgentState(TypedDict):
    conversation_id: str
    tenant_id: str
    tenant_config: Dict[str, Any]  # Serializable tenant data
    messages: List[Any]
    knowledge_context: str
    sicc_memory_context: str      # Novo: Memórias RAG do SICC
    sicc_few_shot_context: str    # Novo: Padrões do SICC (Dynamic Few-Shot)
    intent: str
    lead_data: Dict[str, Any]      # Novo: Dados do lead para personalização
    products_recommended: List[Dict[str, Any]] # Novo: Produtos ofertados (estruturado)
    final_response: str
    should_handoff: bool
    handoff_reason: Optional[str]
    supervisor_feedback: Optional[str] # Novo: Feedback do nó supervisor

# Global default LLM (using global key)
_default_llm = ChatOpenAI(
    model=settings.OPENAI_MODEL, 
    temperature=settings.AGENT_TEMPERATURE,
    openai_api_key=settings.OPENAI_API_KEY
)

def get_llm(tenant_config: Optional[Dict[str, Any]] = None):
    """
    Returns a ChatOpenAI instance with the tenant's API key if available.
    """
    if tenant_config and tenant_config.get("openai_api_key"):
        return ChatOpenAI(
            model=settings.OPENAI_MODEL,
            temperature=settings.AGENT_TEMPERATURE,
            openai_api_key=tenant_config["openai_api_key"]
        )
    return _default_llm

knowledge_service = KnowledgeService()

# Import SICC (Modular)
try:
    from app.ai.sicc.sicc_service import SICCService
    sicc_service = SICCService()
except ImportError:
    sicc_service = None
    print("SICC Service not found. Continuing without it.")

async def load_context(state: AgentState):
    """
    Loads conversation history from Redis.
    """
    memory = RedisMemoryManager()
    history = memory.get_history(state["conversation_id"])
    
    # Convert dicts to LangChain Messages
    lc_messages = []
    for msg in history:
        if msg["role"] == "user":
            lc_messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            lc_messages.append(AIMessage(content=msg["content"]))
    
    # Append current new message (it's passed in state['messages'] usually as the last one or only one)
    # The state['messages'] coming from entrypoint might just be the user input.
    # Let's assume state['messages'] has the current turn input.
    
    full_history = lc_messages + state["messages"]
    
    return {
        "messages": full_history, 
        "knowledge_context": "", 
        "sicc_memory_context": "", 
        "sicc_few_shot_context": ""
    }

async def sicc_retriever(state: AgentState):
    """
    Novo: Nodo SICC que recupera Memória Semântica e Padrões Aprendidos.
    """
    if not sicc_service:
        return {}

    last_message = state["messages"][-1].content
    tenant_id = state["tenant_id"]

    sicc_context = await sicc_service.prepare_context(tenant_id, last_message)

    return {
        "sicc_memory_context": sicc_context["memory_context"],
        "sicc_few_shot_context": sicc_context["few_shot_context"]
    }

async def classify_intent(state: AgentState):
    """
    Classifies the user intent based on the last message.
    """
    last_message = state["messages"][-1].content
    history_text = "\n".join([f"{m.type}: {m.content}" for m in state["messages"][:-1]])
    
    # Dynamic LLM per-tenant
    llm = get_llm(state.get("tenant_config"))
    
    prompt = ChatPromptTemplate.from_template(prompts.INTENT_CLASSIFICATION_PROMPT)
    chain = prompt | llm | StrOutputParser()
    
    intent = await chain.ainvoke({
        "history": history_text[-1000:] if history_text else "Sem histórico", # limit context
        "message": last_message
    })
    
    return {"intent": intent.strip().upper()}

async def search_knowledge(state: AgentState):
    """
    Searches RAG if intent is QUESTION.
    """
    last_message = state["messages"][-1].content
    tenant_id = state["tenant_id"]
    
    context = await knowledge_service.search_relevant(last_message, tenant_id)
    
    return {"knowledge_context": context}

async def generate_response(state: AgentState):
    """
    Generates the final response using Context + RAG.
    """
    tenant_config = state["tenant_config"]
    agent_name = tenant_config.get("agent_name", "BIA")
    
    # 1. Prompt Base com Personalidade
    # Note: 'agent_personality' is not defined in the provided code snippet.
    # Assuming it's a global or imported variable, or a placeholder for future implementation.
    agent_personality = tenant_config.get("agent_personality", "um assistente prestativo") 
    system_prompt_text = prompts.SYSTEM_PROMPT.format(
        agent_name=agent_name,
        agent_personality=agent_personality,
        knowledge_context=state["knowledge_context"] or "Nenhuma informação específica encontrada no banco de conhecimento."
    )

    # 2. Injetar Contexto SICC (Memória de Longo Prazo e Few-Shot)
    if state.get("sicc_memory_context"):
        system_prompt_text += f"\n\n### MEMÓRIA DE CONVERSAS ANTERIORES:\n{state['sicc_memory_context']}"
    
    if state.get("sicc_few_shot_context"):
        system_prompt_text += f"\n{state['sicc_few_shot_context']}"
    
    # 3. Injetar Feedback do Supervisor (Loop de Correção)
    if state.get("supervisor_feedback"):
        system_prompt_text += f"\n\n### ATENÇÃO: SUA RESPOSTA ANTERIOR FOI REPROVADA PELO SUPERVISOR.\n" \
                              f"MOTIVO/DICA: {state['supervisor_feedback']}\n" \
                              f"Por favor, gere uma nova resposta corrigindo os pontos acima."
    
    messages = [SystemMessage(content=system_prompt_text)] + state["messages"]
    
    # Dynamic LLM per-tenant
    llm = get_llm(tenant_config)
    
    response = await llm.ainvoke(messages)
    
    # 3. Registrar interação no SICC para aprendizado futuro (Async sugerido)
    if sicc_service:
        last_user_msg = state["messages"][-1].content
        await sicc_service.store_interaction(
            tenant_id=state["tenant_id"],
            conversation_id=state["conversation_id"],
            content=last_user_msg
        )

    return {"final_response": response.content}

async def evaluate_handoff(state: AgentState):
    """
    Evaluates if handoff constitutes based on response and user input.
    """
    last_user_message = state["messages"][-1].content
    ai_response = state.get("final_response", "")
    
    prompt = ChatPromptTemplate.from_template(prompts.HANDOFF_EVALUATION_PROMPT)
    # Dynamic LLM per-tenant
    llm = get_llm(state.get("tenant_config"))
    # Force JSON output
    json_llm = llm.bind(response_format={"type": "json_object"})
    chain = prompt | json_llm | StrOutputParser()
    
    try:
        result_str = await chain.ainvoke({
            "user_message": last_user_message,
            "ai_response": ai_response
        })
        result = json.loads(result_str)
        
        return {
            "should_handoff": result.get("should_handoff", False),
            "handoff_reason": result.get("reason")
        }
    except Exception as e:
        print(f"Handoff Eval Error: {e}")
        return {"should_handoff": False}

async def sicc_reflection(state: AgentState):
    """
    Novo: Nodo de Reflexão SICC. 
    Analisa a resposta gerada e sugere correções se violar padrões ou o tom do tenant.
    """
    ai_response = state.get("final_response", "")
    few_shot = state.get("sicc_few_shot_context", "")
    
    if not ai_response or not few_shot:
        return {} # Nada para refletir

    # Dynamic LLM per-tenant
    llm = get_llm(state.get("tenant_config"))

    prompt = ChatPromptTemplate.from_template(prompts.SICC_REFLECTION_PROMPT)
    chain = prompt | llm | StrOutputParser()
    
    analysis = await chain.ainvoke({
        "ai_response": ai_response,
        "few_shot_context": few_shot
    })
    
    # Se a resposta começar com [CORRIGIDO], atualizamos a final_response
    if analysis.startswith("[CORRIGIDO]"):
        corrected_response = analysis.replace("[CORRIGIDO]", "").strip()
        return {"final_response": corrected_response}
   
    return {}
