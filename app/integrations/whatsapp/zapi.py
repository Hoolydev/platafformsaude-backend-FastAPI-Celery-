"""
Z-API Provider
"""

from typing import Any, Dict, Optional
import httpx

from app.config import settings
from app.integrations.whatsapp.base import BaseWhatsAppProvider


class ZAPIProvider(BaseWhatsAppProvider):
    """Provider para Z-API."""

    def __init__(self, instance_id: str, token: str, client_token: Optional[str] = None):
        base = (settings.ZAPI_BASE_URL if hasattr(settings, "ZAPI_BASE_URL") else "").rstrip("/")
        self.base_url = f"{base}/instances/{instance_id}/token/{token}"
        self.headers = {"Content-Type": "application/json"}
        if client_token:
            self.headers["client-token"] = client_token

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
        # Z-API não tem endpoint de typing nativo — retorna vazio
        return {}

    def normalize_webhook(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        # Z-API envia mensagens com campo "type"
        msg_type = payload.get("type", "")
        from_number = payload.get("phone", "")

        if not from_number or payload.get("fromMe"):
            return None

        if msg_type == "ReceivedCallback":
            text = payload.get("text", {}).get("message", "")
            if text:
                return {
                    "type": "message",
                    "from": from_number,
                    "message_type": "text",
                    "content": text,
                    "raw": payload,
                }

            image = payload.get("image")
            if image:
                return {
                    "type": "message",
                    "from": from_number,
                    "message_type": "image",
                    "content": image.get("imageUrl", ""),
                    "caption": image.get("caption", ""),
                    "raw": payload,
                }

            audio = payload.get("audio")
            if audio:
                return {
                    "type": "message",
                    "from": from_number,
                    "message_type": "audio",
                    "content": audio.get("audioUrl", ""),
                    "raw": payload,
                }

            document = payload.get("document")
            if document:
                return {
                    "type": "message",
                    "from": from_number,
                    "message_type": "document",
                    "content": document.get("documentUrl", ""),
                    "filename": document.get("fileName", ""),
                    "raw": payload,
                }

        return None
