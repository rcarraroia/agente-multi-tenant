import httpx
import logging
import os
from typing import Dict, Any, List, Optional
from uuid import UUID
from app.core.config import settings

logger = logging.getLogger(__name__)

class AsaasService:
    """
    Serviço de integração com a API V3 do Asaas.
    Focado em Assinaturas e Splits para o Agente Multi-Tenant.
    """
    def __init__(self):
        self.api_key = settings.ASAAS_API_KEY
        self.base_url = settings.ASAAS_BASE_URL  # Ex: https://api.asaas.com/v3
        self.headers = {
            "access_token": self.api_key,
            "Content-Type": "application/json"
        }
        self.timeout = 30.0

    async def create_customer(self, name: str, email: str, cpf_cnpj: str) -> Dict[str, Any]:
        """Cria um cliente no Asaas para faturamento do Tenant."""
        url = f"{self.base_url}/customers"
        payload = {
            "name": name,
            "email": email,
            "cpfCnpj": cpf_cnpj
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(url, json=payload, headers=self.headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Asaas Error (create_customer): {e.response.text}")
                raise e

    async def create_subscription(self, customer_id: str, value: float, cycle: str, splits: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Cria uma assinatura recorrente com divisão de valores (Split).
        Regra: 70% Fixos para Renum via Split ou Recebedor Principal.
        """
        url = f"{self.base_url}/subscriptions"
        payload = {
            "customer": customer_id,
            "billingType": "PIX", # Default PIX/Boleto para facilitar
            "value": value,
            "nextDueDate": "2026-02-01", # Placeholder, ideal calcular D+30
            "cycle": cycle, # WEEKLY, MONTHLY, etc
            "description": "Assinatura Agente Multi-Tenant",
            "splits": splits
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(url, json=payload, headers=self.headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Asaas Error (create_subscription): {e.response.text}")
                raise e

    async def validate_wallet(self, wallet_id: str) -> Dict[str, Any]:
        """Valida se uma Wallet ID de afiliado é válida e ativa no Asaas."""
        url = f"{self.base_url}/wallets/{wallet_id}"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(url, headers=self.headers)
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "is_valid": True,
                        "status": data.get("status"),
                        "name": data.get("name")
                    }
                return {"is_valid": False, "error": "Wallet not found"}
            except Exception as e:
                logger.error(f"Asaas Validation Error: {str(e)}")
                return {"is_valid": False, "error": str(e)}

    def calculate_splits_70_30(self, total_value: float, affiliate_ids: Dict[int, str]) -> List[Dict[str, Any]]:
        """
        Calcula o array de splits conforme a regra de negócio:
        - Renum: 70%
        - N1: 15% (se houver)
        - N2: 3% (se houver)
        - N3: 2% (se houver)
        - Slim Quality/JB: 5% cada + Sobras
        """
        splits = []
        renum_wallet = os.getenv("ASAAS_WALLET_RENUM")
        slim_wallet = os.getenv("ASAAS_WALLET_SLIM_QUALITY")
        jb_wallet = os.getenv("ASAAS_WALLET_JB")

        # 70% Renum
        splits.append({
            "walletId": renum_wallet,
            "fixedValue": round(total_value * 0.70, 2),
            "description": "Plataforma Renum"
        })

        # Pool de 30% (Comissões e Gestores)
        # Nivel 1 (15%)
        n1_wallet = affiliate_ids.get(1)
        if n1_wallet:
            splits.append({"walletId": n1_wallet, "fixedValue": round(total_value * 0.15, 2)})
        
        # ... Lógica de redistribuição de N2/N3 omitida para brevidade no mock inicial
        # Implementação real deve seguir a lógica do SQL migrado.
        
        return splits
