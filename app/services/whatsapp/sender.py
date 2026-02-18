"""
WhatsApp Sender - Envio de mensagens para diferentes providers
"""

from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
import httpx
import time
import os
from app.models.connection import WhatsappConnection, WhatsappProvider


class BaseSender(ABC):
    """Base class para senders de WhatsApp"""
    
    def __init__(self, connection: WhatsappConnection):
        self.connection = connection
        self.credentials = connection.credenciais
    
    @abstractmethod
    async def send_text(self, phone: str, message: str) -> Dict[str, Any]:
        """Envia mensagem de texto"""
        pass
    
    @abstractmethod
    async def send_image(self, phone: str, image_url: str, caption: Optional[str] = None) -> Dict[str, Any]:
        """Envia imagem"""
        pass
    
    @abstractmethod
    async def send_audio(self, phone: str, audio_url: str) -> Dict[str, Any]:
        """Envia áudio"""
        pass
    
    @abstractmethod
    async def send_document(self, phone: str, document_url: str, filename: Optional[str] = None) -> Dict[str, Any]:
        """Envia documento"""
        pass
    
    async def send_with_retry(self, func, *args, max_retries: int = 3, **kwargs) -> Dict[str, Any]:
        """
        Executa função com retry e exponential backoff
        
        Args:
            func: Função async a executar
            max_retries: Número máximo de tentativas
        
        Returns:
            Resultado da função
        """
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    # Exponential backoff: 1s, 2s, 4s
                    wait_time = 2 ** attempt
                    print(f"Tentativa {attempt + 1} falhou: {str(e)}. Aguardando {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"Todas as {max_retries} tentativas falharam")
        
        raise last_exception


class ZAPISender(BaseSender):
    """Sender para Z-API"""
    
    def __init__(self, connection: WhatsappConnection):
        super().__init__(connection)
        self.instance_id = self.credentials.get("instance_id")
        self.token = self.credentials.get("token")
        self.base_url = f"https://api.z-api.io/instances/{self.instance_id}/token/{self.token}"
    
    async def send_text(self, phone: str, message: str) -> Dict[str, Any]:
        """Envia mensagem de texto via Z-API"""
        url = f"{self.base_url}/send-text"
        payload = {
            "phone": phone,
            "message": message
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=30.0)
            response.raise_for_status()
            return response.json()
    
    async def send_image(self, phone: str, image_url: str, caption: Optional[str] = None) -> Dict[str, Any]:
        """Envia imagem via Z-API"""
        url = f"{self.base_url}/send-image"
        payload = {
            "phone": phone,
            "image": image_url,
            "caption": caption or ""
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=30.0)
            response.raise_for_status()
            return response.json()
    
    async def send_audio(self, phone: str, audio_url: str) -> Dict[str, Any]:
        """Envia áudio via Z-API"""
        url = f"{self.base_url}/send-audio"
        payload = {
            "phone": phone,
            "audio": audio_url
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=30.0)
            response.raise_for_status()
            return response.json()
    
    async def send_document(self, phone: str, document_url: str, filename: Optional[str] = None) -> Dict[str, Any]:
        """Envia documento via Z-API"""
        url = f"{self.base_url}/send-document"
        payload = {
            "phone": phone,
            "document": document_url,
            "fileName": filename or "documento.pdf"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=30.0)
            response.raise_for_status()
            return response.json()


class UAZAPISender(BaseSender):
    """Sender para UazAPI"""
    
    def __init__(self, connection: WhatsappConnection):
        super().__init__(connection)
        self.api_key = self.credentials.get("api_key")
        self.instance_id = self.credentials.get("instance_id")
        self.base_url = f"https://api.uazapi.com/v1/instances/{self.instance_id}"
    
    async def send_text(self, phone: str, message: str) -> Dict[str, Any]:
        """Envia mensagem de texto via UazAPI"""
        url = f"{self.base_url}/messages/text"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "to": phone,
            "body": message
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
    
    async def send_image(self, phone: str, image_url: str, caption: Optional[str] = None) -> Dict[str, Any]:
        """Envia imagem via UazAPI"""
        url = f"{self.base_url}/messages/image"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "to": phone,
            "url": image_url,
            "caption": caption or ""
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
    
    async def send_audio(self, phone: str, audio_url: str) -> Dict[str, Any]:
        """Envia áudio via UazAPI"""
        url = f"{self.base_url}/messages/audio"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "to": phone,
            "url": audio_url
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
    
    async def send_document(self, phone: str, document_url: str, filename: Optional[str] = None) -> Dict[str, Any]:
        """Envia documento via UazAPI"""
        url = f"{self.base_url}/messages/document"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "to": phone,
            "url": document_url,
            "filename": filename or "documento.pdf"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()


class OficialSender(BaseSender):
    """Sender para WhatsApp Business API Oficial (Meta)"""
    
    def __init__(self, connection: WhatsappConnection):
        super().__init__(connection)
        self.access_token = self.credentials.get("access_token")
        self.phone_number_id = self.credentials.get("phone_number_id")
        self.base_url = f"https://graph.facebook.com/v18.0/{self.phone_number_id}/messages"
    
    async def send_text(self, phone: str, message: str) -> Dict[str, Any]:
        """Envia mensagem de texto via Meta API"""
        headers = {"Authorization": f"Bearer {self.access_token}"}
        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "text",
            "text": {"body": message}
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(self.base_url, json=payload, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
    
    async def send_image(self, phone: str, image_url: str, caption: Optional[str] = None) -> Dict[str, Any]:
        """Envia imagem via Meta API"""
        headers = {"Authorization": f"Bearer {self.access_token}"}
        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "image",
            "image": {
                "link": image_url,
                "caption": caption or ""
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(self.base_url, json=payload, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
    
    async def send_audio(self, phone: str, audio_url: str) -> Dict[str, Any]:
        """Envia áudio via Meta API"""
        headers = {"Authorization": f"Bearer {self.access_token}"}
        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "audio",
            "audio": {"link": audio_url}
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(self.base_url, json=payload, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
    
    async def send_document(self, phone: str, document_url: str, filename: Optional[str] = None) -> Dict[str, Any]:
        """Envia documento via Meta API"""
        headers = {"Authorization": f"Bearer {self.access_token}"}
        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "document",
            "document": {
                "link": document_url,
                "filename": filename or "documento.pdf"
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(self.base_url, json=payload, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
    
    async def send_template(self, phone: str, template_name: str, language: str = "pt_BR", components: Optional[list] = None) -> Dict[str, Any]:
        """Envia template message via Meta API"""
        headers = {"Authorization": f"Bearer {self.access_token}"}
        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language},
                "components": components or []
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(self.base_url, json=payload, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()


class WhatsAppSender:
    """
    Classe principal para envio de mensagens WhatsApp
    
    Detecta automaticamente o provider e usa o sender apropriado
    """
    
    def __init__(self, connection: WhatsappConnection):
        self.connection = connection
        self.sender = self._get_sender()
    
    def _get_sender(self) -> BaseSender:
        """Retorna o sender apropriado baseado no provider"""
        senders = {
            WhatsappProvider.ZAPI: ZAPISender,
            WhatsappProvider.UAZAPI: UAZAPISender,
            WhatsappProvider.OFICIAL: OficialSender
        }
        
        sender_class = senders.get(self.connection.provider)
        if not sender_class:
            raise ValueError(f"Provider não suportado: {self.connection.provider}")
        
        return sender_class(self.connection)
    
    async def send(self, phone: str, message_type: str, **kwargs) -> Dict[str, Any]:
        """
        Envia mensagem com retry automático
        
        Args:
            phone: Número do telefone
            message_type: "text", "image", "audio", "document", "template"
            **kwargs: Argumentos específicos do tipo de mensagem
        
        Returns:
            Resposta da API
        """
        methods = {
            "text": self.sender.send_text,
            "image": self.sender.send_image,
            "audio": self.sender.send_audio,
            "document": self.sender.send_document,
        }
        
        # Template apenas para API oficial
        if message_type == "template" and isinstance(self.sender, OficialSender):
            methods["template"] = self.sender.send_template
        
        method = methods.get(message_type)
        if not method:
            raise ValueError(f"Tipo de mensagem não suportado: {message_type}")
        
        # Executar com retry
        return await self.sender.send_with_retry(method, phone, **kwargs)
