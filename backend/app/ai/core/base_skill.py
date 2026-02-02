from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseSkill(ABC):
    """
    Interface base para todas as Skills de Negócio.
    Uma Skill é um módulo plugável que adiciona capacidades ao agente.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Slug identificador da skill (ex: product_sales)"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Descrição usada pelo Router para decidir quando usar esta skill"""
        pass

    @abstractmethod
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execução principal da skill.
        Deve retornar um dicionário com atualizações para o estado (AgentState).
        """
        pass
    
    def get_node_name(self) -> str:
        """Nome do nó no grafo LangGraph"""
        return f"skill_{self.name}"
