from typing import Dict, Any, Optional
import httpx
from ..interfaces import IWhatsAppProvider
from ..models import InstanceConfig, ConnectionStatus, QRCodeData, WebhookEvent
import os

class EvolutionProvider(IWhatsAppProvider):
    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            "apikey": self.api_key,
            "Content-Type": "application/json"
        }

    async def create_instance(self, config: InstanceConfig) -> Dict[str, Any]:
        """
        Cria instância na Evolution e configura Chatwoot.
        """
        instance_name = config.instance_name
        
        # 1. Criar Instância
        create_url = f"{self.api_url}/instance/create"
        payload = {
            "instanceName": instance_name,
            "token": config.token or os.getenv("EVOLUTION_INSTANCE_TOKEN", "default-token"),
            "qrcode": True,
            "integration": "WHATSAPP-BAILEYS"
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(create_url, json=payload, headers=self.headers)
            resp.raise_for_status()
            instance_data = resp.json()

        # 2. Configurar Chatwoot (Integração Nativa)
        # Assumindo que config.settings contém dados do chatwoot
        if config.settings and "chatwoot" in config.settings:
            cw_config = config.settings["chatwoot"]
            await self._configure_chatwoot(instance_name, cw_config)

        return instance_data

    async def _configure_chatwoot(self, instance_name: str, config: Dict[str, Any]):
        url = f"{self.api_url}/chatwoot/set/{instance_name}"
        payload = {
            "enabled": True,
            "account_id": config.get("account_id"),
            "token": config.get("token"),
            "url": config.get("url"),
            "sign_msg": True,
            "reopen_conversation": False,
            "conversation_pending": False, # Chatwoot define se é pending via inbox settings ou auto-assignment
            "import_contacts": True,
            "name_inbox": f"WhatsApp {instance_name}"
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, headers=self.headers)
            resp.raise_for_status()

    async def delete_instance(self, instance_id: str) -> bool:
        url = f"{self.api_url}/instance/delete/{instance_id}"
        async with httpx.AsyncClient() as client:
            resp = await client.delete(url, headers=self.headers)
            if resp.status_code == 200:
                return True
            return False

    async def get_connection_status(self, instance_id: str) -> ConnectionStatus:
        url = f"{self.api_url}/instance/connectionState/{instance_id}"
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, headers=self.headers)
                if resp.status_code != 200:
                    return ConnectionStatus.UNDEFINED
                
                data = resp.json()
                # Evolution retorna { "instance": "...", "state": "open" | "close" | "connecting" }
                state = data.get("instance", {}).get("state")
                
                if state == "open":
                    return ConnectionStatus.CONNECTED
                elif state == "close":
                    return ConnectionStatus.DISCONNECTED
                elif state == "connecting":
                    return ConnectionStatus.CONNECTING
                return ConnectionStatus.UNDEFINED
        except:
            return ConnectionStatus.UNDEFINED

    async def get_qr_code(self, instance_id: str) -> Optional[QRCodeData]:
        # Na Evolution v2, chamar /instance/connect/{instance} retorna o base64 se estiver desconectado
        url = f"{self.api_url}/instance/connect/{instance_id}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=self.headers)
            if resp.status_code == 200:
                data = resp.json()
                # Formato: { "code": "...", "base64": "..." }
                if "base64" in data:
                    return QRCodeData(code=data["base64"], type="base64")
                if "code" in data: # Fallback
                     return QRCodeData(code=data["code"], type="base64")
            return None

    async def parse_webhook(self, payload: Dict[str, Any]) -> Optional[WebhookEvent]:
        event_type = payload.get("event")
        instance = payload.get("instance")
        
        if event_type == "qrcode.updated":
            data = payload.get("data", {})
            return WebhookEvent(
                event_type="qrcode_updated",
                instance_id=instance,
                data={"qrcode": data.get("qrcode", {}).get("base64")},
                timestamp=payload.get("date_time", "")
            )
        
        elif event_type == "connection.update":
            data = payload.get("data", {})
            state = data.get("state") # open, close, connecting
            return WebhookEvent(
                event_type="connection_update",
                instance_id=instance,
                data={"status": state, "reason": data.get("statusReason")},
                timestamp=payload.get("date_time", "")
            )
            
        return None
