"""
WhatsApp Business API (Meta Graph API v18.0) Provider
"""

from typing import Any, Dict, Optional
import httpx

from app.integrations.whatsapp.base import BaseWhatsAppProvider

GRAPH_BASE = "https://graph.facebook.com/v18.0"


class OficialProvider(BaseWhatsAppProvider):
    """Provider para WhatsApp Business API oficial (Meta)."""

    def __init__(self, phone_number_id: str, access_token: str):
        self.phone_number_id = phone_number_id
        self.access_token = access_token
        self.base_url = f"{GRAPH_BASE}/{phone_number_id}/messages"
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    async def _post(self, body: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(self.base_url, json=body, headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    async def send_text(self, to: str, text: str, **kwargs) -> Dict[str, Any]:
        return await self._post({
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": text},
        })

    async def send_image(self, to: str, url: str, caption: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        return await self._post({
            "messaging_product": "whatsapp",
            "to": to,
            "type": "image",
            "image": {"link": url, "caption": caption or ""},
        })

    async def send_audio(self, to: str, url: str, **kwargs) -> Dict[str, Any]:
        return await self._post({
            "messaging_product": "whatsapp",
            "to": to,
            "type": "audio",
            "audio": {"link": url},
        })

    async def send_document(self, to: str, url: str, filename: str, **kwargs) -> Dict[str, Any]:
        return await self._post({
            "messaging_product": "whatsapp",
            "to": to,
            "type": "document",
            "document": {"link": url, "filename": filename},
        })

    async def send_typing(self, to: str, **kwargs) -> Dict[str, Any]:
        # Meta API não suporta typing indicator via REST — retorna vazio
        return {}

    def normalize_webhook(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parseia formato Meta Webhook."""
        try:
            entry = payload.get("entry", [{}])[0]
            changes = entry.get("changes", [{}])[0]
            value = changes.get("value", {})
            messages = value.get("messages", [])

            if not messages:
                return None

            msg = messages[0]
            from_number = msg.get("from", "")
            msg_type = msg.get("type", "")

            if msg_type == "text":
                return {
                    "type": "message",
                    "from": from_number,
                    "message_type": "text",
                    "content": msg.get("text", {}).get("body", ""),
                    "raw": payload,
                }

            if msg_type == "image":
                return {
                    "type": "message",
                    "from": from_number,
                    "message_type": "image",
                    "content": msg.get("image", {}).get("id", ""),  # media_id para download
                    "caption": msg.get("image", {}).get("caption", ""),
                    "raw": payload,
                }

            if msg_type == "audio":
                return {
                    "type": "message",
                    "from": from_number,
                    "message_type": "audio",
                    "content": msg.get("audio", {}).get("id", ""),
                    "raw": payload,
                }

            if msg_type == "document":
                return {
                    "type": "message",
                    "from": from_number,
                    "message_type": "document",
                    "content": msg.get("document", {}).get("id", ""),
                    "filename": msg.get("document", {}).get("filename", ""),
                    "raw": payload,
                }

        except (IndexError, KeyError, TypeError):
            pass

        return None
