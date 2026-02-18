"""
Humanizer - Quebra mensagens longas e calcula delays para simular digitação humana
"""

import re
import random
from typing import List, Dict, Any


class MessageHumanizer:
    """
    Quebra mensagens longas em partes menores e calcula delays de digitação
    
    Baseado nos workflows n8n para parecer mais humano
    """
    
    def __init__(
        self,
        max_chars_per_message: int = 150,
        ms_per_char: int = 50,
        variation_percent: float = 0.2
    ):
        self.max_chars = max_chars_per_message
        self.ms_per_char = ms_per_char
        self.variation = variation_percent
    
    def humanize(self, text: str) -> List[Dict[str, Any]]:
        """
        Quebra texto em mensagens menores com delays calculados
        
        Args:
            text: Texto completo a ser enviado
        
        Returns:
            Lista de {conteudo: str, delay_ms: int, tipo: str}
        """
        # Quebrar em partes menores
        parts = self._split_text(text)
        
        # Calcular delays para cada parte
        messages = []
        for part in parts:
            delay = self._calculate_delay(part)
            messages.append({
                "conteudo": part.strip(),
                "delay_ms": delay,
                "tipo": "text"
            })
        
        return messages
    
    def _split_text(self, text: str) -> List[str]:
        """
        Quebra texto em partes menores respeitando pontuação natural
        
        Prioridade de quebra:
        1. Parágrafos (\n\n)
        2. Pontos finais (.)
        3. Vírgulas (,)
        4. Espaços
        """
        # Se texto é curto, retornar como está
        if len(text) <= self.max_chars:
            return [text]
        
        parts = []
        
        # Primeiro, quebrar por parágrafos
        paragraphs = text.split('\n\n')
        
        for paragraph in paragraphs:
            if len(paragraph) <= self.max_chars:
                parts.append(paragraph)
            else:
                # Quebrar por sentenças (pontos)
                sentences = re.split(r'([.!?]+\s+)', paragraph)
                
                current_part = ""
                for i in range(0, len(sentences), 2):
                    sentence = sentences[i]
                    punctuation = sentences[i + 1] if i + 1 < len(sentences) else ""
                    
                    full_sentence = sentence + punctuation
                    
                    # Se adicionar esta sentença ultrapassar o limite
                    if len(current_part) + len(full_sentence) > self.max_chars:
                        # Se current_part não está vazio, adicionar
                        if current_part:
                            parts.append(current_part.strip())
                            current_part = full_sentence
                        else:
                            # Sentença muito longa, quebrar por vírgulas
                            parts.extend(self._split_by_commas(full_sentence))
                    else:
                        current_part += full_sentence
                
                # Adicionar última parte
                if current_part:
                    parts.append(current_part.strip())
        
        return [p for p in parts if p]  # Remover vazios
    
    def _split_by_commas(self, text: str) -> List[str]:
        """Quebra texto longo por vírgulas"""
        parts = []
        chunks = re.split(r'(,\s+)', text)
        
        current_part = ""
        for i in range(0, len(chunks), 2):
            chunk = chunks[i]
            comma = chunks[i + 1] if i + 1 < len(chunks) else ""
            
            full_chunk = chunk + comma
            
            if len(current_part) + len(full_chunk) > self.max_chars:
                if current_part:
                    parts.append(current_part.strip())
                    current_part = full_chunk
                else:
                    # Chunk muito longo, quebrar por espaços
                    parts.extend(self._split_by_spaces(full_chunk))
            else:
                current_part += full_chunk
        
        if current_part:
            parts.append(current_part.strip())
        
        return parts
    
    def _split_by_spaces(self, text: str) -> List[str]:
        """Quebra texto por espaços (último recurso)"""
        words = text.split()
        parts = []
        current_part = ""
        
        for word in words:
            if len(current_part) + len(word) + 1 > self.max_chars:
                if current_part:
                    parts.append(current_part.strip())
                current_part = word
            else:
                current_part += " " + word if current_part else word
        
        if current_part:
            parts.append(current_part.strip())
        
        return parts
    
    def _calculate_delay(self, text: str) -> int:
        """
        Calcula delay de digitação baseado no tamanho do texto
        
        Fórmula: (chars * ms_per_char) ± variação aleatória
        """
        base_delay = len(text) * self.ms_per_char
        
        # Adicionar variação aleatória (±20% por padrão)
        variation_amount = base_delay * self.variation
        random_variation = random.uniform(-variation_amount, variation_amount)
        
        final_delay = int(base_delay + random_variation)
        
        # Mínimo de 500ms, máximo de 5000ms
        return max(500, min(5000, final_delay))


# Exemplo de uso
if __name__ == "__main__":
    humanizer = MessageHumanizer()
    
    text = """
    Olá! Tudo bem? Seja bem-vindo à Clínica Saúde Total. 
    Vejo aqui que você gostaria de agendar uma consulta com o Dr. João Silva. 
    Temos os seguintes horários disponíveis para esta semana: 
    Segunda-feira às 14h, terça-feira às 10h e quarta-feira às 16h. 
    Qual horário seria melhor para você?
    """
    
    messages = humanizer.humanize(text)
    
    for i, msg in enumerate(messages, 1):
        print(f"\nMensagem {i}:")
        print(f"Conteúdo: {msg['conteudo']}")
        print(f"Delay: {msg['delay_ms']}ms")
