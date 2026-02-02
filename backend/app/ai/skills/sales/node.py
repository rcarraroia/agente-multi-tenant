import structlog
from typing import Dict, Any
from app.ai.core.base_skill import BaseSkill
from app.services.product_service import ProductService

logger = structlog.get_logger(__name__)

class SalesSkill(BaseSkill):
    """
    Skill de Vendas: Consultar catálogo global e ofertar produtos.
    """
    
    @property
    def name(self) -> str:
        return "product_sales"

    @property
    def description(self) -> str:
        return "Ideal para quando o usuário demonstra interesse em comprar, pergunta sobre preços ou modelos de colchões."

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executa a lógica de vendas: busca produtos e prepara a recomendação.
        """
        logger.info("Executing SalesSkill", tenant_id=state.get("tenant_id"))
        
        service = ProductService()
        # Busca produtos (pode vir de filtros do state no futuro)
        products = await service.get_active_products(limit=3)
        
        # Injeta os produtos formatados para o próximo nó (Geração/Supervisor)
        products_context = service.format_for_prompt(products)
        
        # Adiciona ao lead_data para memória
        lead_data = state.get("lead_data", {})
        lead_data["last_products_shown"] = [p["name"] for p in products]
        
        return {
            "products_recommended": products,
            "knowledge_context": f"\n\n### PRODUTOS DISPONÍVEIS (Catálogo Slim Quality):\n{products_context}\n\n"
                                 f"DIRETRIZ DE VENDA: Foque no parcelamento em 12x. Não dê descontos no preço de tabela.",
            "lead_data": lead_data
        }
