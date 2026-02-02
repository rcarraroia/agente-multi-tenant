from abc import ABC, abstractmethod
from typing import Dict, Optional, Any
from .models import InstanceConfig, ConnectionStatus, QRCodeData, WebhookEvent

class IWhatsAppProvider(ABC):
    """
    Interface para provedores de WhatsApp (Evolution, Uazapi, etc).
    Focada em infraestrutura e gestão de conexão.
    """

    @abstractmethod
    async def create_instance(self, config: InstanceConfig) -> Dict[str, Any]:
        """
        Cria uma nova instância no provedor e configura os webhooks e integrações nativas (ex: Chatwoot).
        Retorna os dados da instância criada.
        """
        pass

    @abstractmethod
    async def delete_instance(self, instance_id: str) -> bool:
        """
        Remove uma instância e limpa recursos associados.
        """
        pass

    @abstractmethod
    async def get_connection_status(self, instance_id: str) -> ConnectionStatus:
        """
        Retorna o status atual da conexão.
        """
        pass

    @abstractmethod
    async def get_qr_code(self, instance_id: str) -> Optional[QRCodeData]:
        """
        Retorna o QR Code atual para leitura, se disponível.
        """
        pass

    @abstractmethod
    async def parse_webhook(self, payload: Dict[str, Any]) -> Optional[WebhookEvent]:
        """
        Analisa o payload de um webhook do provedor e retorna um evento normalizado
        (apenas eventos de infraestrutura: QR Code, Status).
        Retorna None se o evento não for relevante.
        """
        pass
