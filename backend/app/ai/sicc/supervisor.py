from typing import List, Dict, Any, Optional
from uuid import UUID
import logging
from app.db.supabase import get_supabase

logger = logging.getLogger(__name__)

class SupervisorEngine:
    """
    Motor Supervisor do SICC 2.0.
    Processa a fila de aprendizado e auto-aprova padrões com alta confiança.
    """
    def __init__(self, auto_approve_threshold: float = 0.85):
        self.supabase = get_supabase()
        self.auto_approve_threshold = auto_approve_threshold

    async def process_pending_learnings(self, tenant_id: Optional[UUID] = None):
        """Varre a fila de logs e move para Patterns se aprovado."""
        try:
            query = self.supabase.table("sicc_learning_logs").select("*").eq("status", "pending")
            if tenant_id:
                query = query.eq("tenant_id", str(tenant_id))
            
            pending = query.execute()

            for log in pending.data:
                score = log.get("confidence_score", 0.0)
                if score >= self.auto_approve_threshold:
                    await self.approve_learning(log["id"])
                    logger.info(f"SICC: Padrão auto-aprovado automaticamente (Score: {score})")
                
        except Exception as e:
            logger.error(f"Erro ao processar supervisão SICC: {e}")

    async def approve_learning(self, log_id: UUID):
        """Aprova manualmente ou via sistema um aprendizado e o torna ativo."""
        try:
            # 1. Buscar dados do log
            log_res = self.supabase.table("sicc_learning_logs").select("*").eq("id", str(log_id)).execute()
            if not log_res.data:
                return False
            
            log = log_res.data[0]
            p_data = log["pattern_data"]

            # 2. Criar o padrão real
            new_pattern = {
                "tenant_id": log["tenant_id"],
                "name": p_data.get("name", "Novo Padrão"),
                "type": p_data.get("type", "general"),
                "trigger_condition": p_data.get("trigger_condition"),
                "response_template": p_data.get("response_template"),
                "confidence_score": log["confidence_score"],
                "is_active": True,
                "metadata": {"source_log": str(log_id)}
            }

            self.supabase.table("sicc_behavior_patterns").insert(new_pattern).execute()

            # 3. Atualizar status do log
            self.supabase.table("sicc_learning_logs").update({
                "status": "approved",
                "reviewer_notes": "Aprovado automaticamente pelo Supervisor SICC"
            }).eq("id", str(log_id)).execute()

            return True
        except Exception as e:
            logger.error(f"Erro na aprovação SICC: {e}")
            return False
