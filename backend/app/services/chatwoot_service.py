import httpx
from typing import Dict, Any, Optional
import os
from fastapi import HTTPException

class ChatwootService:
    def __init__(self):
        self.api_url = os.getenv("CHATWOOT_URL")
        self.api_token = os.getenv("CHATWOOT_ADMIN_TOKEN") # Or user/agent token
        if not self.api_url or not self.api_token:
            # For now, just print warning or pass, but in prod should raise
            print("Warning: Chatwoot not configured properly")

        self.headers = {
            "api_access_token": self.api_token,
            "Content-Type": "application/json"
        }

    async def send_message(self, account_id: int, conversation_id: int, content: str, message_type: str = "outgoing"):
        """
        Send a message to a conversation.
        """
        url = f"{self.api_url}/api/v1/accounts/{account_id}/conversations/{conversation_id}/messages"
        payload = {
            "content": content,
            "message_type": message_type,
            "private": False
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, headers=self.headers)
            if resp.status_code >= 400:
                print(f"Error sending message to Chatwoot: {resp.text}")
                # Don't raise strict error to avoid crashing webhook processing
                return None
            return resp.json()

    async def toggle_status(self, account_id: int, conversation_id: int, status: str):
        """
        Change conversation status (open, resolved, pending, snoozed).
        """
        url = f"{self.api_url}/api/v1/accounts/{account_id}/conversations/{conversation_id}/toggle_status"
        payload = {"status": status}
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    async def get_conversation(self, account_id: int, conversation_id: int):
        url = f"{self.api_url}/api/v1/accounts/{account_id}/conversations/{conversation_id}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=self.headers)
            resp.raise_for_status()
            return resp.json()
