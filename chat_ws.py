from fastapi import WebSocket, WebSocketDisconnect
from collections import defaultdict

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.messages = []  # stores messages + reactions

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, data: dict):
        for connection in self.active_connections:
            await connection.send_json(data)

manager = ConnectionManager()

async def chat_endpoint(websocket: WebSocket, user: str):
    await manager.connect(websocket)

    try:
        while True:
            data = await websocket.receive_json()

            # 💬 TEXT MESSAGE
            if data["type"] == "message":
                msg = {
                    "type": "message",
                    "user": user,
                    "text": data["text"],
                    "reactions": defaultdict(list)
                }
                manager.messages.append(msg)
                await manager.broadcast(msg)

            # 🖼️ IMAGE MESSAGE
            elif data["type"] == "image":
                msg = {
                    "type": "image",
                    "user": user,
                    "image": data["image"],
                    "reactions": defaultdict(list)
                }
                manager.messages.append(msg)
                await manager.broadcast(msg)

            # ❤️ REACTION (IMPORTANT)
            elif data["type"] == "reaction":
                index = data["index"]
                emoji = data["emoji"]

                # ❌ DO NOT CREATE NEW MESSAGE
                if user not in manager.messages[index]["reactions"][emoji]:
                    manager.messages[index]["reactions"][emoji].append(user)

                # ✅ ONLY UPDATE EXISTING MESSAGE
                await manager.broadcast({
                    "type": "reaction",
                    "index": index,
                    "reactions": manager.messages[index]["reactions"]
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket)
