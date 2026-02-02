import structlog
from typing import List, Dict, Any, Optional
from app.db.supabase import get_supabase

logger = structlog.get_logger(__name__)

class ProductService:
    """
    Serviço para consulta de produtos no catálogo global da Slim Quality.
    Consome a tabela public.products existente.
    """
    
    def __init__(self):
        self.supabase = get_supabase()

    async def get_active_products(self, limit: int = 5, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Busca produtos ativos com tratamento de preço (cents -> reais).
        """
        try:
            query = self.supabase.table("products").select("*").eq("is_active", True)
            
            if category:
                query = query.eq("category", category)
                
            response = query.limit(limit).execute()
            
            products = []
            for item in response.data:
                # Conversão segura de centavos para reais (round 2 casas)
                price_cents = item.get("price_cents", 0)
                price_reais = round(price_cents / 100.0, 2)
                
                products.append({
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "description": item.get("description"),
                    "price": price_reais,
                    "image_url": item.get("image_url"),
                    "sku": item.get("sku"),
                    "metadata": {
                        "dimensions": f"{item.get('width_cm', 0)}x{item.get('length_cm', 0)}x{item.get('height_cm', 0)}cm",
                        "weight": f"{item.get('weight_kg', 0)}kg",
                        "warranty": f"{item.get('warranty_years', 0)} anos"
                    }
                })
                
            return products
            
        except Exception as e:
            logger.error("Error fetching products", error=str(e))
            return []

    def format_for_prompt(self, products: List[Dict[str, Any]]) -> str:
        """
        Formata a lista de produtos para ser injetada no prompt do LLM.
        """
        if not products:
            return "Nenhum produto disponível no momento."
            
        formatted = []
        for i, p in enumerate(products, 1):
            formatted.append(
                f"{i}. **{p['name']}**\n"
                f"   - Descrição: {p['description']}\n"
                f"   - Preço: R$ {p['price']:.2f}\n"
                f"   - Especificações: {p['metadata']['dimensions']}, {p['metadata']['warranty']} de garantia"
            )
        return "\n\n".join(formatted)
