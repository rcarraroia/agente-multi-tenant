from typing import Optional, Dict, Any, List
from uuid import UUID
import logging
from .memory import MemoryEngine
from .behavior import BehaviorEngine
from .learning import LearningEngine
from .supervisor import SupervisorEngine
from .interfaces import MemoryChunk

logger = logging.getLogger(__name__)

class SICCService:
    """
    Orquestrador Modular SICC 2.0.
    Ponto de entrada único para o sistema de inteligência.
    """
    def __init__(self):
        self.memory = MemoryEngine()
        self.behavior = BehaviorEngine()
        self.learning = LearningEngine()
        self.supervisor = SupervisorEngine()

    async def prepare_context(self, tenant_id: UUID, message: str) -> Dict[str, Any]:
        """
        Prepara o contexto rico para o Agente (Memórias + Padrões).
        """
        # 1. Buscar memórias relevantes (RAG)
        memories = await self.memory.search(tenant_id, message, limit=3)
        memory_text = "\n".join([m.content for m in memories])

        # 2. Buscar padrões e build Few-Shot
        patterns = await self.behavior.get_active_patterns(tenant_id, message)
        few_shot_context = await self.behavior.build_dynamic_few_shot(tenant_id, patterns)

        return {
            "memory_context": memory_text,
            "few_shot_context": few_shot_context,
            "patterns": patterns
        }

    async def store_interaction(self, tenant_id: UUID, conversation_id: UUID, content: str):
        """Armazena a interação atual para aprendizado futuro."""
        chunk = MemoryChunk(
            tenant_id=tenant_id,
            conversation_id=conversation_id,
            content=content
        )
        return await self.memory.store(chunk)

    async def analyze_conversation(self, tenant_id: UUID, conversation_id: UUID):
        """
        Gatilho assíncrono para analisar uma conversa e extrair aprendizados.
        Geralmente chamado após o encerramento da conversa ou handoff.
        """
        logger.info(f"SICC: Iniciando análise da conversa {conversation_id}")
        
        # 1. Extrair Padrões
        patterns = await self.learning.extract_patterns(conversation_id, tenant_id)
        
        # 2. Sugerir Aprendizado
        if patterns:
            await self.learning.suggest_learning(patterns, tenant_id, conversation_id)
            logger.info(f"SICC: {len(patterns)} novos padrões sugeridos.")
            
            # 3. Processar Supervisão (Auto-Aprovação)
            await self.supervisor.process_pending_learnings(tenant_id)
        else:
            logger.info("SICC: Nenhum padrão relevante identificado.")
