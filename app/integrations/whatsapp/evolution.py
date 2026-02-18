"""
Evolution API Provider
"""

from typing import Any, Dict, Optional
import httpx

from app.config import settings
from app.integrations.whatsapp.base import BaseWhatsAppProvider


class EvolutionProvider(BaseWhatsAppProvider):
    """Provider para Evolution API."""

    def __init__(self, instance: str, api_url: Optional[str] = None, api_key: Optional[str] = None):
        self.instance = instance
        self.base_url = (api_url or settings.EVOLUTION_API_URL).rstrip("/")
        self.api_key = api_key or settings.EVOLUTION_API_KEY
        self.headers = {"apikey": self.api_key, "Content-Type": "application/json"}

    async def _post(self, path: str, body: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{self.base_url}{path}", json=body, headers=self.headers)
            resp.raise_for_status()
            return resp.json()

    async def send_text(self, to: str, text: str, **kwargs) -> Dict[str, Any]:
        return await self._post(
            f"/message/sendText/{self.instance}",
            {"number": to, "text": text},
        )

    async def send_image(self, to: str, url: str, caption: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        return await self._post(
            f"/message/sendMedia/{self.instance}",
            {
                "number": to,
                "mediatype": "image",
                "media": url,
                "caption": caption or "",
            },
        )

    async def send_audio(self, to: str, url: str, **kwargs) -> Dict[str, Any]:
        return await self._post(
            f"/message/sendWhatsAppAudio/{self.instance}",
            {"number": to, "audio": url, "encoding": True},
        )

    async def send_document(self, to: str, url: str, filename: str, **kwargs) -> Dict[str, Any]:
        return await self._post(
            f"/message/sendMedia/{self.instance}",
            {
                "number": to,
                "mediatype": "document",
                "media": url,
                "fileName": filename,
            },
        )

    async def send_typing(self, to: str, **kwargs) -> Dict[str, Any]:
        return await self._post(
            f"/message/sendPresence/{self.instance}",
            {"number": to, "presence": "composing"},
        )

    def normalize_webhook(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        event = payload.get("event", "")

        # Atualização de conexão
        if event == "connection.update":
            return {
                "type": "connection",
                "status": payload.get("data", {}).get("state"),
                "raw": payload,
            }

        # Mensagem recebida
        if event == "messages.upsert":
            data = payload.get("data", {})
            key = data.get("key", {})

            # Ignorar mensagens enviadas pelo próprio bot
            if key.get("fromMe"):
                return None

            from_number = key.get("remoteJid", "").replace("@s.whatsapp.net", "")
            msg = data.get("message", {})

            # Texto simples
            if "conversation" in msg:
                return {
                    "type": "message",
                    "from": from_number,
                    "message_type": "text",
                    "content": msg["conversation"],
                    "raw": payload,
                }

            # Texto estendido
            if "extendedTextMessage" in msg:
                return {
                    "type": "message",
                    "from": from_number,
                    "message_type": "text",
                    "content": msg["extendedTextMessage"].get("text", ""),
                    "raw": payload,
                }

            # Imagem
            if "imageMessage" in msg:
                return {
                    "type": "message",
                    "from": from_number,
                    "message_type": "image",
                    "content": msg["imageMessage"].get("url", ""),
                    "caption": msg["imageMessage"].get("caption", ""),
                    "raw": payload,
                }

            # Áudio
            if "audioMessage" in msg:
                return {
                    "type": "message",
                    "from": from_number,
                    "message_type": "audio",
                    "content": msg["audioMessage"].get("url", ""),
                    "raw": payload,
                }

            # Documento
            if "documentMessage" in msg:
                return {
                    "type": "message",
                    "from": from_number,
                    "message_type": "document",
                    "content": msg["documentMessage"].get("url", ""),
                    "filename": msg["documentMessage"].get("fileName", ""),
                    "raw": payload,
                }

        return None
