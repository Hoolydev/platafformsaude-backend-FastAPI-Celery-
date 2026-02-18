"""
Voice - Integração com ElevenLabs para síntese de voz
"""

import httpx
import os
from typing import Optional
import base64


class ElevenLabsVoice:
    """
    Integração com ElevenLabs para converter texto em áudio
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ELEVENLABS_API_KEY")
        self.base_url = "https://api.elevenlabs.io/v1"
    
    async def text_to_speech(
        self,
        text: str,
        voice_id: str,
        model_id: str = "eleven_multilingual_v2",
        stability: float = 0.5,
        similarity_boost: float = 0.75
    ) -> bytes:
        """
        Converte texto em áudio usando ElevenLabs
        
        Args:
            text: Texto a converter
            voice_id: ID da voz no ElevenLabs
            model_id: Modelo a usar
            stability: Estabilidade da voz (0-1)
            similarity_boost: Similaridade com voz original (0-1)
        
        Returns:
            Bytes do arquivo de áudio (MP3)
        """
        url = f"{self.base_url}/text-to-speech/{voice_id}"
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }
        
        data = {
            "text": text,
            "model_id": model_id,
            "voice_settings": {
                "stability": stability,
                "similarity_boost": similarity_boost
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=data,
                headers=headers,
                timeout=30.0
            )
            response.raise_for_status()
            return response.content
    
    async def text_to_speech_base64(
        self,
        text: str,
        voice_id: str,
        **kwargs
    ) -> str:
        """
        Converte texto em áudio e retorna como base64
        
        Útil para enviar diretamente via WhatsApp
        """
        audio_bytes = await self.text_to_speech(text, voice_id, **kwargs)
        return base64.b64encode(audio_bytes).decode('utf-8')
    
    async def get_available_voices(self) -> list:
        """
        Lista vozes disponíveis na conta ElevenLabs
        
        Returns:
            Lista de vozes com id, name, labels
        """
        url = f"{self.base_url}/voices"
        
        headers = {
            "Accept": "application/json",
            "xi-api-key": self.api_key
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            return data.get("voices", [])


class WhisperTranscription:
    """
    Integração com OpenAI Whisper para transcrição de áudio
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = "https://api.openai.com/v1"
    
    async def transcribe_audio(
        self,
        audio_file: bytes,
        filename: str = "audio.ogg",
        language: str = "pt"
    ) -> str:
        """
        Transcreve áudio usando Whisper
        
        Args:
            audio_file: Bytes do arquivo de áudio
            filename: Nome do arquivo (para mimetype)
            language: Código do idioma (pt, en, es, etc)
        
        Returns:
            Texto transcrito
        """
        url = f"{self.base_url}/audio/transcriptions"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        
        files = {
            "file": (filename, audio_file, "audio/ogg")
        }
        
        data = {
            "model": "whisper-1",
            "language": language,
            "response_format": "text"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=headers,
                files=files,
                data=data,
                timeout=60.0
            )
            response.raise_for_status()
            return response.text
    
    async def transcribe_from_url(
        self,
        audio_url: str,
        **kwargs
    ) -> str:
        """
        Baixa áudio de URL e transcreve
        
        Args:
            audio_url: URL do arquivo de áudio
        
        Returns:
            Texto transcrito
        """
        # Baixar áudio
        async with httpx.AsyncClient() as client:
            response = await client.get(audio_url, timeout=30.0)
            response.raise_for_status()
            audio_bytes = response.content
        
        # Transcrever
        return await self.transcribe_audio(audio_bytes, **kwargs)


# Exemplo de uso
if __name__ == "__main__":
    import asyncio
    
    async def test_elevenlabs():
        voice = ElevenLabsVoice()
        
        # Listar vozes disponíveis
        voices = await voice.get_available_voices()
        print("Vozes disponíveis:")
        for v in voices[:3]:
            print(f"- {v['name']} (ID: {v['voice_id']})")
        
        # Converter texto em áudio
        if voices:
            voice_id = voices[0]['voice_id']
            audio = await voice.text_to_speech(
                "Olá! Seja bem-vindo à clínica.",
                voice_id
            )
            print(f"\nÁudio gerado: {len(audio)} bytes")
    
    # asyncio.run(test_elevenlabs())
