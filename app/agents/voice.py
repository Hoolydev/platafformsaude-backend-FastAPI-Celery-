"""
Tool: ElevenLabs TTS
"""

from typing import Optional
import httpx

from app.config import settings

ELEVENLABS_BASE = "https://api.elevenlabs.io/v1"


async def text_to_speech(text: str, voice_id: str, model_id: Optional[str] = "eleven_multilingual_v2") -> bytes:
    """
    Converte texto em áudio MP3 via ElevenLabs.

    Returns:
        bytes: conteúdo MP3 do áudio gerado
    """
    url = f"{ELEVENLABS_BASE}/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": settings.ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    body = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
        },
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(url, json=body, headers=headers)
        resp.raise_for_status()
        return resp.content
