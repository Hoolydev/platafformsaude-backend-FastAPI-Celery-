"""
WhatsApp Message Parsers - Normalização de mensagens de diferentes providers
"""

from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum


class MessageType(str, Enum):
    """Tipos de mensagem suportados"""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    DOCUMENT = "document"
    VIDEO = "video"
    STICKER = "sticker"
    LOCATION = "location"
    CONTACT = "contact"


class NormalizedMessage:
    """Mensagem normalizada de qualquer provider"""
    
    def __init__(
        self,
        telefone: str,
        nome_contato: Optional[str],
        tipo_mensagem: MessageType,
        conteudo: str,
        midia_url: Optional[str] = None,
        mimetype: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        external_id: Optional[str] = None,
        metadados: Optional[Dict[str, Any]] = None
    ):
        self.telefone = telefone
        self.nome_contato = nome_contato
        self.tipo_mensagem = tipo_mensagem
        self.conteudo = conteudo
        self.midia_url = midia_url
        self.mimetype = mimetype
        self.timestamp = timestamp or datetime.utcnow()
        self.external_id = external_id
        self.metadados = metadados or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário"""
        return {
            "telefone": self.telefone,
            "nome_contato": self.nome_contato,
            "tipo_mensagem": self.tipo_mensagem.value,
            "conteudo": self.conteudo,
            "midia_url": self.midia_url,
            "mimetype": self.mimetype,
            "timestamp": self.timestamp.isoformat(),
            "external_id": self.external_id,
            "metadados": self.metadados
        }


class ZAPIParser:
    """Parser para webhooks da Z-API"""
    
    @staticmethod
    def parse(payload: Dict[str, Any]) -> NormalizedMessage:
        """
        Parse webhook da Z-API
        
        Formato esperado:
        {
            "phone": "5511999999999",
            "senderName": "João Silva",
            "messageId": "msg_123",
            "text": {"message": "Olá"},
            "image": {"imageUrl": "...", "caption": "..."},
            "timestamp": 1234567890
        }
        """
        telefone = payload.get("phone", "").replace("+", "")
        nome_contato = payload.get("senderName")
        external_id = payload.get("messageId")
        timestamp = datetime.fromtimestamp(payload.get("timestamp", 0))
        
        # Detectar tipo de mensagem
        if "text" in payload:
            return NormalizedMessage(
                telefone=telefone,
                nome_contato=nome_contato,
                tipo_mensagem=MessageType.TEXT,
                conteudo=payload["text"].get("message", ""),
                timestamp=timestamp,
                external_id=external_id
            )
        
        elif "image" in payload:
            return NormalizedMessage(
                telefone=telefone,
                nome_contato=nome_contato,
                tipo_mensagem=MessageType.IMAGE,
                conteudo=payload["image"].get("caption", ""),
                midia_url=payload["image"].get("imageUrl"),
                mimetype=payload["image"].get("mimeType", "image/jpeg"),
                timestamp=timestamp,
                external_id=external_id
            )
        
        elif "audio" in payload:
            return NormalizedMessage(
                telefone=telefone,
                nome_contato=nome_contato,
                tipo_mensagem=MessageType.AUDIO,
                conteudo="[Áudio]",
                midia_url=payload["audio"].get("audioUrl"),
                mimetype=payload["audio"].get("mimeType", "audio/ogg"),
                timestamp=timestamp,
                external_id=external_id
            )
        
        elif "document" in payload:
            return NormalizedMessage(
                telefone=telefone,
                nome_contato=nome_contato,
                tipo_mensagem=MessageType.DOCUMENT,
                conteudo=payload["document"].get("fileName", "[Documento]"),
                midia_url=payload["document"].get("documentUrl"),
                mimetype=payload["document"].get("mimeType", "application/pdf"),
                timestamp=timestamp,
                external_id=external_id
            )
        
        elif "video" in payload:
            return NormalizedMessage(
                telefone=telefone,
                nome_contato=nome_contato,
                tipo_mensagem=MessageType.VIDEO,
                conteudo=payload["video"].get("caption", "[Vídeo]"),
                midia_url=payload["video"].get("videoUrl"),
                mimetype=payload["video"].get("mimeType", "video/mp4"),
                timestamp=timestamp,
                external_id=external_id
            )
        
        elif "sticker" in payload:
            return NormalizedMessage(
                telefone=telefone,
                nome_contato=nome_contato,
                tipo_mensagem=MessageType.STICKER,
                conteudo="[Sticker]",
                midia_url=payload["sticker"].get("stickerUrl"),
                timestamp=timestamp,
                external_id=external_id
            )
        
        elif "location" in payload:
            loc = payload["location"]
            return NormalizedMessage(
                telefone=telefone,
                nome_contato=nome_contato,
                tipo_mensagem=MessageType.LOCATION,
                conteudo=f"Localização: {loc.get('latitude')}, {loc.get('longitude')}",
                timestamp=timestamp,
                external_id=external_id,
                metadados={
                    "latitude": loc.get("latitude"),
                    "longitude": loc.get("longitude"),
                    "address": loc.get("address")
                }
            )
        
        else:
            # Fallback para texto
            return NormalizedMessage(
                telefone=telefone,
                nome_contato=nome_contato,
                tipo_mensagem=MessageType.TEXT,
                conteudo="[Mensagem não suportada]",
                timestamp=timestamp,
                external_id=external_id
            )


class UAZAPIParser:
    """Parser para webhooks da UazAPI"""
    
    @staticmethod
    def parse(payload: Dict[str, Any]) -> NormalizedMessage:
        """
        Parse webhook da UazAPI
        
        Formato similar à Z-API com pequenas diferenças
        """
        # UazAPI tem formato similar, adaptar conforme necessário
        telefone = payload.get("from", "").replace("+", "")
        nome_contato = payload.get("pushName")
        external_id = payload.get("id")
        timestamp = datetime.fromtimestamp(payload.get("timestamp", 0))
        
        msg_type = payload.get("type", "text")
        
        if msg_type == "text":
            return NormalizedMessage(
                telefone=telefone,
                nome_contato=nome_contato,
                tipo_mensagem=MessageType.TEXT,
                conteudo=payload.get("body", ""),
                timestamp=timestamp,
                external_id=external_id
            )
        
        elif msg_type == "image":
            return NormalizedMessage(
                telefone=telefone,
                nome_contato=nome_contato,
                tipo_mensagem=MessageType.IMAGE,
                conteudo=payload.get("caption", ""),
                midia_url=payload.get("url"),
                mimetype=payload.get("mimetype", "image/jpeg"),
                timestamp=timestamp,
                external_id=external_id
            )
        
        # Adicionar outros tipos conforme necessário
        else:
            return NormalizedMessage(
                telefone=telefone,
                nome_contato=nome_contato,
                tipo_mensagem=MessageType.TEXT,
                conteudo="[Mensagem não suportada]",
                timestamp=timestamp,
                external_id=external_id
            )


class OficialParser:
    """Parser para webhooks da WhatsApp Business API Oficial (Meta)"""
    
    @staticmethod
    def parse(payload: Dict[str, Any]) -> NormalizedMessage:
        """
        Parse webhook da Meta WhatsApp Business API
        
        Formato:
        {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "from": "5511999999999",
                            "id": "wamid.xxx",
                            "timestamp": "1234567890",
                            "type": "text",
                            "text": {"body": "Olá"}
                        }],
                        "contacts": [{
                            "profile": {"name": "João Silva"}
                        }]
                    }
                }]
            }]
        }
        """
        try:
            entry = payload["entry"][0]
            change = entry["changes"][0]
            value = change["value"]
            message = value["messages"][0]
            contact = value.get("contacts", [{}])[0]
            
            telefone = message.get("from", "").replace("+", "")
            nome_contato = contact.get("profile", {}).get("name")
            external_id = message.get("id")
            timestamp = datetime.fromtimestamp(int(message.get("timestamp", 0)))
            msg_type = message.get("type")
            
            if msg_type == "text":
                return NormalizedMessage(
                    telefone=telefone,
                    nome_contato=nome_contato,
                    tipo_mensagem=MessageType.TEXT,
                    conteudo=message["text"]["body"],
                    timestamp=timestamp,
                    external_id=external_id
                )
            
            elif msg_type == "image":
                image_data = message["image"]
                return NormalizedMessage(
                    telefone=telefone,
                    nome_contato=nome_contato,
                    tipo_mensagem=MessageType.IMAGE,
                    conteudo=image_data.get("caption", ""),
                    midia_url=image_data.get("id"),  # Precisa fazer download via API
                    mimetype=image_data.get("mime_type", "image/jpeg"),
                    timestamp=timestamp,
                    external_id=external_id,
                    metadados={"media_id": image_data.get("id")}
                )
            
            elif msg_type == "audio":
                audio_data = message["audio"]
                return NormalizedMessage(
                    telefone=telefone,
                    nome_contato=nome_contato,
                    tipo_mensagem=MessageType.AUDIO,
                    conteudo="[Áudio]",
                    midia_url=audio_data.get("id"),
                    mimetype=audio_data.get("mime_type", "audio/ogg"),
                    timestamp=timestamp,
                    external_id=external_id,
                    metadados={"media_id": audio_data.get("id")}
                )
            
            elif msg_type == "document":
                doc_data = message["document"]
                return NormalizedMessage(
                    telefone=telefone,
                    nome_contato=nome_contato,
                    tipo_mensagem=MessageType.DOCUMENT,
                    conteudo=doc_data.get("filename", "[Documento]"),
                    midia_url=doc_data.get("id"),
                    mimetype=doc_data.get("mime_type"),
                    timestamp=timestamp,
                    external_id=external_id,
                    metadados={"media_id": doc_data.get("id")}
                )
            
            elif msg_type == "location":
                loc_data = message["location"]
                return NormalizedMessage(
                    telefone=telefone,
                    nome_contato=nome_contato,
                    tipo_mensagem=MessageType.LOCATION,
                    conteudo=f"Localização: {loc_data.get('latitude')}, {loc_data.get('longitude')}",
                    timestamp=timestamp,
                    external_id=external_id,
                    metadados={
                        "latitude": loc_data.get("latitude"),
                        "longitude": loc_data.get("longitude"),
                        "name": loc_data.get("name"),
                        "address": loc_data.get("address")
                    }
                )
            
            else:
                return NormalizedMessage(
                    telefone=telefone,
                    nome_contato=nome_contato,
                    tipo_mensagem=MessageType.TEXT,
                    conteudo="[Mensagem não suportada]",
                    timestamp=timestamp,
                    external_id=external_id
                )
        
        except (KeyError, IndexError) as e:
            raise ValueError(f"Formato de webhook inválido: {str(e)}")


def parse_webhook_message(provider: str, payload: Dict[str, Any]) -> NormalizedMessage:
    """
    Parse webhook de qualquer provider
    
    Args:
        provider: "zapi", "uazapi" ou "oficial"
        payload: Payload do webhook
    
    Returns:
        NormalizedMessage
    """
    parsers = {
        "zapi": ZAPIParser,
        "uazapi": UAZAPIParser,
        "oficial": OficialParser
    }
    
    parser_class = parsers.get(provider.lower())
    if not parser_class:
        raise ValueError(f"Provider não suportado: {provider}")
    
    return parser_class.parse(payload)
