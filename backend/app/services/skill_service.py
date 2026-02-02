import structlog
from typing import List, Dict, Any
from app.db.supabase import get_supabase
from app.ai.core.registry import SkillRegistry

logger = structlog.get_logger(__name__)

class SkillService:
    """
    Gerencia as permissões e ativação de skills por tenant.
    """
    
    def __init__(self):
        self.supabase = get_supabase()

    async def get_active_skills_for_tenant(self, tenant_id: str) -> List[Dict[str, Any]]:
        """
        Busca as skills ativas do tenant no banco de dados.
        """
        try:
            # Query join tenant_skills com skills
            response = self.supabase.table("tenant_skills") \
                .select("is_active, config, skills(slug, name, description)") \
                .eq("tenant_id", tenant_id) \
                .eq("is_active", True) \
                .execute()
            
            active_skills = []
            for item in response.data:
                skill_meta = item.get("skills")
                if skill_meta:
                    active_skills.append({
                        "id": skill_meta.get("slug"),
                        "name": skill_meta.get("name"),
                        "description": skill_meta.get("description"),
                        "config": item.get("config", {})
                    })
            
            return active_skills
        except Exception as e:
            logger.error("Error fetching tenant skills", error=str(e))
            return []

    def get_skill_instances(self, active_skills: List[Dict[str, Any]]):
        """
        Retorna as instâncias das skills a partir do Registry.
        """
        instances = []
        for s in active_skills:
            try:
                instances.append(SkillRegistry.get_skill(s['id']))
            except ValueError:
                logger.warning(f"Skill registered in DB but not in code registry: {s['id']}")
        return instances
