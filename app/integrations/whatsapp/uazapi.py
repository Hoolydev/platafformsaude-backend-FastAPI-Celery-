"""
UAZAPI Provider
"""

from typing import Any, Dict, Optional
import httpx

from app.config import settings
from app.integrations.whatsapp.base import BaseWhatsAppProvider


class UAZAPIProvider(BaseWhatsAppProvider):
    """Provider para UAZAPI."""

    def __init__(self, instance_id: str, token: str):
        base = (settings.UAZAPI_BASE_URL if hasattr(settings, "UAZAPI_BASE_URL") else "").rstrip("/")
        self.base_url = f"{base}/instances/{instance_id}/token/{token}"
        self.headers = {"Content-Type": "application/json", "token": token}

    async def _post(self, path: str, body: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{self.base_url}{path}", json=body, headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    async def send_text(self, to: str, text: str, **kwargs) -> Dict[str, Any]:
        return await self._post("/send-text", {"phone": to, "message": text})

    async def send_image(self, to: str, url: str, caption: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        return await self._post("/send-image", {"phone": to, "image": url, "caption": caption or ""})

    async def send_audio(self, to: str, url: str, **kwargs) -> Dict[str, Any]:
        return await self._post("/send-audio", {"phone": to, "audio": url})

    async def send_document(self, to: str, url: str, filename: str, **kwargs) -> Dict[str, Any]:
        return await self._post("/send-document", {"phone": to, "document": url, "fileName": filename})

    async def send_typing(self, to: str, **kwargs) -> Dict[str, Any]:
        return {}

    def normalize_webhook(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        # UAZAPI usa formato similar ao Z-API
        event = payload.get("event", "")
        from_number = payload.get("sender", "")

        if not from_number or payload.get("fromMe"):
            return None

        if event in ("message", "messages.upsert"):
            msg = payload.get("message", {})
            text = msg.get("text") or msg.get("conversation", "")
            if text:
                return {
                    "type": "message",
                    "from": from_number,
                    "message_type": "text",
                    "content": text,
                    "raw": payload,
                }

            if msg.get("imageUrl"):
                return {
                    "type": "message",
                    "from": from_number,
                    "message_type": "image",
                    "content": msg["imageUrl"],
                    "caption": msg.get("caption", ""),
                    "raw": payload,
                }

            if msg.get("audioUrl"):
                return {
                    "type": "message",
                    "from": from_number,
                    "message_type": "audio",
                    "content": msg["audioUrl"],
                    "raw": payload,
                }

            if msg.get("documentUrl"):
                return {
                    "type": "message",
                    "from": from_number,
                    "message_type": "document",
                    "content": msg["documentUrl"],
                    "filename": msg.get("fileName", ""),
                    "raw": payload,
                }

        return None
