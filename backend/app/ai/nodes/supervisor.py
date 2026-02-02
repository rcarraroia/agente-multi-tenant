import structlog
import json
from typing import Dict, Any, List
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from app.config import settings

logger = structlog.get_logger(__name__)

class SupervisorNode:
    """
    Nó Supervisor: Valida a resposta final do agente contra os dados reais.
    Garante que preços não foram alterados e que o tom é adequado.
    """
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.OPENAI_MODEL, 
            temperature=0, # Rigidez na validação
            openai_api_key=settings.OPENAI_API_KEY
        )

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analisa a final_response e aprova ou solicita correção.
        """
        final_response = state.get("final_response", "")
        products_offered = state.get("products_recommended", [])
        
        if not final_response:
            return {}

        # Prompt de Supervisão
        supervisor_prompt = f"""
        Você é um Supervisor de Qualidade para um Agente de Vendas de Colchões.
        Sua tarefa é garantir que as informações dadas pelo agente ao cliente sejam 100% precisas.

        ### DADOS REAIS DO SISTEMA (VERDADE):
        {json.dumps(products_offered, indent=2)}

        ### RESPOSTA DO AGENTE PARA O CLIENTE:
        "{final_response}"

        ### REGRAS DE VALIDAÇÃO:
        1. O preço citado para qualquer produto deve bater EXATAMENTE com o preço nos dados reais.
        2. O agente NÃO PODE dar descontos (apenas parcelamento em 12x).
        3. O agente deve ser cortês e profissional.

        RESPOSTA ESPERADA (JSON):
        {{
            "is_approved": true/false,
            "reason": "Explicação detalhada caso reprovado",
            "correction_hint": "Dica específica de como o agente deve corrigir a resposta"
        }}
        """

        try:
            # Forçar retorno JSON
            json_llm = self.llm.bind(response_format={"type": "json_object"})
            response = await json_llm.ainvoke([SystemMessage(content=supervisor_prompt)])
            result = json.loads(response.content)
            
            if not result.get("is_approved"):
                logger.warning("Supervisor REPROVED response", reason=result.get("reason"))
                return {
                    "supervisor_feedback": result.get("correction_hint"),
                    "final_response": f"[REPROVADO] {result.get('reason')}" # Temporário para debug no grafo
                }
            
            logger.info("Supervisor APPROVED response")
            return {"supervisor_feedback": None}
            
        except Exception as e:
            logger.error("Supervisor Node Error", error=str(e))
            return {}
