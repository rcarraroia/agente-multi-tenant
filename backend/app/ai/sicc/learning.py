from typing import List, Dict, Any, Optional
from uuid import UUID
import json
import logging
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from app.config import settings
from .interfaces import BaseLearning
from app.db.supabase import get_supabase

logger = logging.getLogger(__name__)

class LearningEngine(BaseLearning):
    """
    Motor de Aprendizado do SICC 2.0.
    Analisa conversas para extrair padrões e sugerir novos comportamentos.
    """
    def __init__(self):
        self.supabase = get_supabase()
        self.llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            temperature=0, # Zero para extração determinística
            openai_api_key=settings.OPENAI_API_KEY
        )

    async def extract_patterns(self, conversation_id: UUID, tenant_id: UUID) -> List[Dict[str, Any]]:
        """Extrai padrões de uma conversa específica."""
        try:
            # 1. Recuperar mensagens da conversa no Supabase
            messages_res = self.supabase.table("multi_agent_conversations")\
                .select("id, messages")\
                .eq("id", str(conversation_id))\
                .execute()
            
            if not messages_res.data:
                return []
            
            # TODO: No futuro as mensagens podem vir do Redis para maior agilidade
            raw_messages = messages_res.data[0].get("messages", [])
            if not raw_messages:
                return []

            # 2. Prompt de Extração
            prompt = ChatPromptTemplate.from_template("""
            Analise o diálogo abaixo entre um Agente e um Cliente e extraia PADRÕES COMPORTAMENTAIS.
            Um padrão ocorre quando o Agente resolve um problema, responde uma dúvida complexa ou segue um processo eficaz.

            DIÁLOGO:
            {chat_history}

            EXTRATO EM JSON:
            {{
                "patterns": [
                    {{
                        "name": "Nome curto do padrão",
                        "type": "discovery/sales/support/preference",
                        "trigger_condition": "O que o cliente disse ou qual a situação?",
                        "response_template": "Como o agente deve responder ou agir?",
                        "confidence_score": 0.0 a 1.0,
                        "reasoning": "Por que este padrão é relevante?"
                    }}
                ]
            }}
            """)
            
            chain = prompt | self.llm | JsonOutputParser()
            
            chat_text = "\n".join([f"{m['role']}: {m['content']}" for m in raw_messages])
            result = await chain.ainvoke({"chat_history": chat_text})
            
            return result.get("patterns", [])

        except Exception as e:
            logger.error(f"Erro ao extrair padrões SICC: {e}")
            return []

    async def suggest_learning(self, patterns: List[Dict[str, Any]], tenant_id: UUID, conversation_id: Optional[UUID] = None) -> bool:
        """Registra as sugestões de aprendizado no banco para aprovação."""
        if not patterns:
            return False

        try:
            insert_data = []
            for p in patterns:
                insert_data.append({
                    "tenant_id": str(tenant_id),
                    "conversation_id": str(conversation_id) if conversation_id else None,
                    "pattern_data": p,
                    "confidence_score": p.get("confidence_score", 0.0),
                    "status": "pending"
                })
            
            self.supabase.table("sicc_learning_logs").insert(insert_data).execute()
            return True
        except Exception as e:
            logger.error(f"Erro ao sugerir aprendizado SICC: {e}")
            return False
