from app.ai.core.registry import SkillRegistry
from app.ai.skills.sales.node import SalesSkill

# Registrar as skills disponíveis no sistema
SkillRegistry.register(SalesSkill)
