from langgraph.graph import StateGraph, END
from app.ai.nodes import (
    AgentState,
    load_context,
    classify_intent,
    generate_response,
    evaluate_handoff,
    sicc_retriever,
    search_knowledge,
    sicc_reflection
)
from app.ai.core.registry import SkillRegistry
from app.ai.core.router import SkillRouter
from app.ai.nodes.supervisor import SupervisorNode

async def dynamic_skill_router(state: AgentState):
    """
    Roteador de habilidades: baseado nas skills ativas do tenant (virão no config futuramente).
    Por enquanto, usa as skills registradas no código para decidir o caminho.
    """
    # Em produção, carregaríamos apenas as skills do tenant via SkillService.
    # Para este MVP, usaremos todas as skills registradas que o tenant tenha ativas.
    # Simplificação: O state['intent'] pode ser usado para ajudar o router.
    
    active_skills_metadata = []
    for skill_name in SkillRegistry.list_skills():
        instance = SkillRegistry.get_skill(skill_name)
        active_skills_metadata.append({
            "name": instance.name,
            "description": instance.description
        })
    
    router = SkillRouter(active_skills_metadata)
    decision = await router.route(state)
    return decision

def supervisor_router(state: AgentState):
    """
    Verifica se o Supervisor aprovou a resposta.
    """
    if state.get("supervisor_feedback"):
        return "generate" # Loop de correção (idealmente limitado a 1 vez)
    return "sicc_reflection"

def build_agent_graph():
    workflow = StateGraph(AgentState)

    # 1. Add Default Nodes
    workflow.add_node("load_context", load_context)
    workflow.add_node("sicc_retriever", sicc_retriever)
    workflow.add_node("rag_search", search_knowledge)
    workflow.add_node("generate", generate_response)
    workflow.add_node("sicc_reflection", sicc_reflection)
    workflow.add_node("check_handoff", evaluate_handoff)
    
    # 2. Add Supervisor Node
    supervisor = SupervisorNode()
    workflow.add_node("supervisor", supervisor.execute)

    # 3. Add Dynamic Skill Nodes
    for skill_name in SkillRegistry.list_skills():
        skill_instance = SkillRegistry.get_skill(skill_name)
        
        # Criamos um wrapper para o nó do grafo
        async def skill_node_wrapper(state, inst=skill_instance):
            update = await inst.execute(state)
            return update
            
        workflow.add_node(f"skill_{skill_name}", skill_node_wrapper)
        # Todas as skills convergem para a geração de resposta
        workflow.add_edge(f"skill_{skill_name}", "generate")

    # Entry Point
    workflow.set_entry_point("load_context")

    # Normal Edges
    workflow.add_edge("load_context", "sicc_retriever")
    
    # Dynamic Routing to Skills or General
    workflow.add_conditional_edges(
        "sicc_retriever",
        dynamic_skill_router
    )

    workflow.add_edge("rag_search", "generate")
    
    # Resposta -> Supervisor
    workflow.add_edge("generate", "supervisor")
    
    # Supervisor -> Loop ou Próximo
    workflow.add_conditional_edges(
        "supervisor",
        supervisor_router,
        {
            "generate": "generate",
            "sicc_reflection": "sicc_reflection"
        }
    )

    workflow.add_edge("sicc_reflection", "check_handoff")
    workflow.add_edge("check_handoff", END)

    return workflow.compile()
