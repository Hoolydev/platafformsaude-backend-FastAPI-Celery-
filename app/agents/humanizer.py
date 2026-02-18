"""
Humanizer — quebra e temporiza mensagens para parecerem humanas
"""

import random
import re
from typing import List, Dict, Any

MAX_CHUNK_LEN = 150
MS_PER_CHAR = 50
JITTER = 0.20  # ±20%

# Padrões de quebra natural (em ordem de preferência)
_BREAK_PATTERNS = [
    r"\n\n",          # parágrafo
    r"\n",            # quebra de linha
    r"(?<=[.!?])\s+", # fim de frase
    r"(?<=,)\s+",     # vírgula
]


def split_message(text: str) -> List[str]:
    """
    Quebra o texto em partes de até MAX_CHUNK_LEN caracteres,
    priorizando quebras em pontuação natural.
    """
    text = text.strip()
    if len(text) <= MAX_CHUNK_LEN:
        return [text]

    chunks: List[str] = []

    # Tenta quebrar por padrões naturais primeiro
    for pattern in _BREAK_PATTERNS:
        parts = re.split(pattern, text)
        if len(parts) > 1:
            # Agrupa partes pequenas em chunks de até MAX_CHUNK_LEN
            current = ""
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                if len(current) + len(part) + 1 <= MAX_CHUNK_LEN:
                    current = f"{current} {part}".strip() if current else part
                else:
                    if current:
                        chunks.append(current)
                    current = part
            if current:
                chunks.append(current)
            if all(len(c) <= MAX_CHUNK_LEN for c in chunks):
                return chunks
            # Se ainda há chunks grandes, continua para próximo padrão
            chunks = []

    # Fallback: quebra forçada por tamanho
    words = text.split()
    current = ""
    for word in words:
        if len(current) + len(word) + 1 <= MAX_CHUNK_LEN:
            current = f"{current} {word}".strip() if current else word
        else:
            if current:
                chunks.append(current)
            current = word
    if current:
        chunks.append(current)

    return chunks if chunks else [text]


def calculate_delay(text: str) -> int:
    """
    Retorna delay em ms: 50ms por caractere com variação aleatória de ±20%.
    Mínimo de 500ms, máximo de 5000ms.
    """
    base = len(text) * MS_PER_CHAR
    jitter = random.uniform(1 - JITTER, 1 + JITTER)
    delay = int(base * jitter)
    return max(500, min(delay, 5000))


def prepare_messages(text: str) -> List[Dict[str, Any]]:
    """
    Retorna lista de {conteudo, delay_ms} prontos para envio humanizado.
    """
    parts = split_message(text)
    return [
        {"conteudo": part, "delay_ms": calculate_delay(part)}
        for part in parts
    ]
