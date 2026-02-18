"""
WebSocket Endpoints - Comunicação em tempo real
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from typing import Dict, Set
import json
from app.auth.jwt import verify_token

router = APIRouter()

# Gerenciador de conexões WebSocket
class ConnectionManager:
    """Gerencia conexões WebSocket por tenant"""
    
    def __init__(self):
        # tenant_id -> Set[WebSocket]
        self.active_connections: Dict[int, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, tenant_id: int):
        """Conecta um WebSocket a um tenant"""
        await websocket.accept()
        
        if tenant_id not in self.active_connections:
            self.active_connections[tenant_id] = set()
        
        self.active_connections[tenant_id].add(websocket)
        print(f"WebSocket conectado ao tenant {tenant_id}. Total: {len(self.active_connections[tenant_id])}")
    
    def disconnect(self, websocket: WebSocket, tenant_id: int):
        """Desconecta um WebSocket"""
        if tenant_id in self.active_connections:
            self.active_connections[tenant_id].discard(websocket)
            print(f"WebSocket desconectado do tenant {tenant_id}. Total: {len(self.active_connections[tenant_id])}")
            
            # Limpar se não houver mais conexões
            if not self.active_connections[tenant_id]:
                del self.active_connections[tenant_id]
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Envia mensagem para um WebSocket específico"""
        await websocket.send_text(message)
    
    async def broadcast_to_tenant(self, tenant_id: int, message: dict):
        """Envia mensagem para todos os WebSockets de um tenant"""
        if tenant_id not in self.active_connections:
            return
        
        message_text = json.dumps(message)
        
        # Enviar para todas as conexões do tenant
        disconnected = set()
        for connection in self.active_connections[tenant_id]:
            try:
                await connection.send_text(message_text)
            except Exception as e:
                print(f"Erro ao enviar mensagem WebSocket: {str(e)}")
                disconnected.add(connection)
        
        # Remover conexões que falharam
        for connection in disconnected:
            self.active_connections[tenant_id].discard(connection)


# Instância global do gerenciador
manager = ConnectionManager()


async def get_current_user_from_token(token: str) -> dict:
    """Valida token JWT e retorna dados do usuário"""
    payload = verify_token(token)
    if not payload:
        raise WebSocketDisconnect(code=1008, reason="Token inválido")
    
    return payload


@router.websocket("/ws/{tenant_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    tenant_id: int,
    token: str = Query(...)
):
    """
    WebSocket endpoint para comunicação em tempo real
    
    Eventos suportados:
    - nova_mensagem: Nova mensagem recebida
    - conversa_atualizada: Status da conversa mudou
    - agente_escalou: Agente escalou para humano
    - digitando: Alguém está digitando
    - atendente_assumiu: Atendente assumiu conversa
    
    Uso:
    ```javascript
    const ws = new WebSocket('ws://localhost:8000/api/v1/ws/1?token=SEU_TOKEN');
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('Evento:', data.event, data);
    };
    
    // Enviar evento
    ws.send(JSON.stringify({
        event: 'digitando',
        conversation_id: 123
    }));
    ```
    """
    # Validar token
    try:
        user_data = await get_current_user_from_token(token)
        
        # Verificar se o tenant do usuário corresponde
        if user_data.get("tenant_id") != tenant_id:
            await websocket.close(code=1008, reason="Tenant inválido")
            return
    
    except Exception as e:
        await websocket.close(code=1008, reason=str(e))
        return
    
    # Conectar
    await manager.connect(websocket, tenant_id)
    
    try:
        # Enviar mensagem de boas-vindas
        await manager.send_personal_message(
            json.dumps({
                "event": "connected",
                "tenant_id": tenant_id,
                "user_id": user_data.get("user_id")
            }),
            websocket
        )
        
        # Loop de recebimento de mensagens
        while True:
            # Receber mensagem do cliente
            data = await websocket.receive_text()
            message = json.loads(data)
            
            event = message.get("event")
            
            # Processar eventos do cliente
            if event == "digitando":
                # Broadcast para outros usuários do tenant
                await manager.broadcast_to_tenant(tenant_id, {
                    "event": "digitando",
                    "conversation_id": message.get("conversation_id"),
                    "user_id": user_data.get("user_id")
                })
            
            elif event == "ping":
                # Responder pong
                await manager.send_personal_message(
                    json.dumps({"event": "pong"}),
                    websocket
                )
            
            else:
                # Echo de volta (para debug)
                await manager.send_personal_message(
                    json.dumps({"event": "echo", "data": message}),
                    websocket
                )
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, tenant_id)
    
    except Exception as e:
        print(f"Erro no WebSocket: {str(e)}")
        manager.disconnect(websocket, tenant_id)


async def broadcast_to_tenant(tenant_id: int, message: dict):
    """
    Função helper para broadcast de mensagens
    
    Pode ser chamada de qualquer lugar do código
    """
    await manager.broadcast_to_tenant(tenant_id, message)


# Exemplos de uso em outros módulos:
"""
# Notificar nova mensagem
from app.api.v1.websocket import broadcast_to_tenant

await broadcast_to_tenant(tenant_id, {
    "event": "nova_mensagem",
    "conversation_id": 123,
    "message_id": 456,
    "preview": "Olá, tudo bem?"
})

# Notificar conversa atualizada
await broadcast_to_tenant(tenant_id, {
    "event": "conversa_atualizada",
    "conversation_id": 123,
    "status": "assumido",
    "atendente_id": 5
})

# Notificar agente escalou
await broadcast_to_tenant(tenant_id, {
    "event": "agente_escalou",
    "conversation_id": 123,
    "motivo": "Cliente solicitou falar com humano"
})
"""
