from typing import List, Dict, Any, Optional
from uuid import UUID
from app.db.supabase import get_supabase
import logging

logger = logging.getLogger(__name__)

class BehaviorEngine:
    """
    Motor de Comportamento do SICC 2.0.
    Responsável por identificar padrões ativos e preparar o Dynamic Few-Shot.
    """
    def __init__(self):
        self.supabase = get_supabase()

    async def get_active_patterns(self, tenant_id: UUID, query: str) -> List[Dict[str, Any]]:
        """
        Busca padrões comportamentais ativos que casam com a intenção/texto.
        Nota: No futuro, isso pode usar busca vetorial também para os triggers.
        """
        try:
            result = self.supabase.table("sicc_behavior_patterns")\
                .select("*")\
                .eq("tenant_id", str(tenant_id))\
                .eq("is_active", True)\
                .execute()
            
            # TODO: Implementar lógica de casamento semântico (Match) mais avançada
            # Por enquanto, retorna os padrões para o tenant processar no prompt
            return result.data
        except Exception as e:
            logger.error(f"Erro ao buscar padrões de comportamento: {e}")
            return []

    async def build_dynamic_few_shot(self, tenant_id: UUID, patterns: List[Dict[str, Any]]) -> str:
        """
        Constrói o bloco de Dynamic Few-Shot para injetar no prompt do sistema.
        """
        if not patterns:
            return ""

        context_block = "\n### EXEMPLOS DE COMPORTAMENTO APRENDIDO (SICC):\n"
        for p in patterns:
            context_block += f"- QUANDO: {p['trigger_condition']}\n"
            context_block += f"  RESPOSTA SUGERIDA: {p['response_template']}\n"
        
        return context_block
