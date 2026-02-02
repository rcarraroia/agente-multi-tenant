import structlog
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.config import settings

logger = structlog.get_logger(__name__)

class SkillRouter:
    """
    Roteador dinâmico: Decide para qual Skill (nó) enviar a conversa baseando-se nas
    Skills ativas do tenant e na descrição de cada uma.
    """
    
    def __init__(self, active_skills_metadata: List[Dict[str, str]]):
        self.llm = ChatOpenAI(
            model=settings.OPENAI_MODEL, 
            temperature=0, 
            openai_api_key=settings.OPENAI_API_KEY
        )
        self.active_skills = active_skills_metadata

    async def route(self, state: Dict[str, Any]) -> str:
        """
        Determina o nome do próximo nó.
        """
        last_message = state["messages"][-1].content
        
        skills_description = "\n".join([
            f"- {s['name']}: {s['description']}" for s in self.active_skills
        ])
        
        router_prompt = f"""
        Você é um roteador inteligente para um sistema multi-agente.
        Com base na última mensagem do usuário, escolha a habilidade MAIS ADEQUADA entre as disponíveis.

        ### HABILIDADES ATIVAS:
        {skills_description}
        - general: Use para conversas genéricas, saudações ou dúvidas que não se encaixam acima.

        ### MENSAGEM DO USUÁRIO:
        "{last_message}"

        Responda APENAS com o nome da habilidade (slug) ou 'general'.
        """
        
        response = await self.llm.ainvoke(router_prompt)
        decision = response.content.strip().lower()
        
        logger.info("Router decision", decision=decision)
        
        # Mapear para nome do nó
        if decision == "general":
            return "generate"
        
        # Encontra se a skill existe nas ativas
        for s in self.active_skills:
            if s['name'] == decision:
                return f"skill_{decision}"
                
        return "generate"
