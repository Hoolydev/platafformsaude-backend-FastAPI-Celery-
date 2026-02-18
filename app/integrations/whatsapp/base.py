"""
Base abstrata para providers WhatsApp
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseWhatsAppProvider(ABC):
    """Classe base para todos os providers WhatsApp."""

    @abstractmethod
    async def send_text(self, to: str, text: str, **kwargs) -> Dict[str, Any]:
        """Envia mensagem de texto."""
        ...

    @abstractmethod
    async def send_image(self, to: str, url: str, caption: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Envia imagem."""
        ...

    @abstractmethod
    async def send_audio(self, to: str, url: str, **kwargs) -> Dict[str, Any]:
        """Envia áudio."""
        ...

    @abstractmethod
    async def send_document(self, to: str, url: str, filename: str, **kwargs) -> Dict[str, Any]:
        """Envia documento."""
        ...

    @abstractmethod
    async def send_typing(self, to: str, **kwargs) -> Dict[str, Any]:
        """Envia indicador de digitação."""
        ...

    @abstractmethod
    def normalize_webhook(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Normaliza o payload do webhook para formato interno.

        Retorna dict com:
          - type: 'message' | 'status' | 'connection'
          - from: número do remetente
          - message_type: 'text' | 'image' | 'audio' | 'document'
          - content: texto ou URL do mídia
          - raw: payload original
        Retorna None se o evento não deve ser processado.
        """
        ...
