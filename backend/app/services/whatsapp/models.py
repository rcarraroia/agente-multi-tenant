from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, HttpUrl

class ConnectionStatus(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    WAITING_QR = "waiting_qr"
    CONNECTING = "connecting"
    UNDEFINED = "undefined"

class InstanceConfig(BaseModel):
    instance_name: str
    tenant_id: str
    token: Optional[str] = None
    integration_type: str = "evolution" # evolution, uazapi
    settings: Optional[Dict[str, Any]] = {}

class QRCodeData(BaseModel):
    code: str # Base64 or raw string
    type: str = "base64" # base64, url

class WebhookEvent(BaseModel):
    event_type: str # qrcode_updated, connection_update
    instance_id: str
    data: Dict[str, Any]
    timestamp: str

class ProviderConfig(BaseModel):
    api_url: HttpUrl
    api_key: str
    webhook_url: HttpUrl
