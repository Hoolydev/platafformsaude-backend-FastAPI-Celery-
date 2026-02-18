"""
WhatsApp Provider Factory
"""

from typing import Dict, Any

from app.integrations.whatsapp.base import BaseWhatsAppProvider
from app.integrations.whatsapp.evolution import EvolutionProvider
from app.integrations.whatsapp.zapi import ZAPIProvider
from app.integrations.whatsapp.uazapi import UAZAPIProvider
from app.integrations.whatsapp.oficial import OficialProvider


class WhatsAppFactory:
    """
    Retorna o provider correto baseado no campo provider da WhatsappConnection.

    Credenciais esperadas por provider:
      evolution:  { instance, api_url?, api_key? }
      zapi:       { instance_id, token, client_token? }
      uazapi:     { instance_id, token }
      oficial:    { phone_number_id, access_token }
    """

    @staticmethod
    def get_provider(provider_type: str, credentials: Dict[str, Any]) -> BaseWhatsAppProvider:
        if provider_type == "evolution":
            return EvolutionProvider(
                instance=credentials["instance"],
                api_url=credentials.get("api_url"),
                api_key=credentials.get("api_key"),
            )

        if provider_type == "zapi":
            return ZAPIProvider(
                instance_id=credentials["instance_id"],
                token=credentials["token"],
                client_token=credentials.get("client_token"),
            )

        if provider_type == "uazapi":
            return UAZAPIProvider(
                instance_id=credentials["instance_id"],
                token=credentials["token"],
            )

        if provider_type == "oficial":
            return OficialProvider(
                phone_number_id=credentials["phone_number_id"],
                access_token=credentials["access_token"],
            )

        raise ValueError(f"Provider desconhecido: {provider_type!r}. "
                         f"Use: evolution, zapi, uazapi, oficial")
