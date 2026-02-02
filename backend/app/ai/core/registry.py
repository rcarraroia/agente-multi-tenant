import structlog
from typing import Dict, Type, List
from app.ai.core.base_skill import BaseSkill

logger = structlog.get_logger(__name__)

class SkillRegistry:
    """
    Registro central de Skills disponíveis.
    Responsável por instanciar as skills solicitadas.
    """
    _registry: Dict[str, Type[BaseSkill]] = {}

    @classmethod
    def register(cls, skill_cls: Type[BaseSkill]):
        """Registra uma classe de Skill"""
        instance = skill_cls() # Instancia temporária apenas para pegar o nome
        cls._registry[instance.name] = skill_cls
        logger.info(f"Skill registered: {instance.name}")

    @classmethod
    def get_skill(cls, skill_slug: str) -> BaseSkill:
        """Retorna uma instância da Skill solicitada"""
        skill_cls = cls._registry.get(skill_slug)
        if not skill_cls:
            raise ValueError(f"Skill not found: {skill_slug}")
        return skill_cls()

    @classmethod
    def list_skills(cls) -> List[str]:
        return list(cls._registry.keys())
