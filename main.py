from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
from typing import Dict
import random
from uuid import uuid4

# ================== APP ==================
app = FastAPI(
    title="Secure Chat Backend",
    version="1.0.0"
)

# ✅ CORS (RENDER + REACT SAFE)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # later restrict to frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ OPTIONS PREFLIGHT HANDLER (IMPORTANT FOR RENDER)
@app.options("/{path:path}")
async def preflight_handler(path: str):
    return {}
    
@app.head("/")
def root_head():
    return


# ✅ ROOT (HEALTH CHECK)
@app.get("/")
def root():
    return {"status": "Secure Chat Backend Running 🚀"}

# ================== CONFIG ==================
OTP_EXPIRY_MINUTES = 4
OTP_STORE: Dict[str, dict] = {}

# ================== MODELS ==================
class LoginRequest(BaseModel):
    email: EmailStr

class VerifyRequest(BaseModel):
    email: EmailStr
    otp: str

# ================== OTP HELPERS ==================
def generate_otp() -> str:
    return str(random.randint(100000, 999999))

# ================== OTP ROUTES ==================
@app.post("/send-otp")
def send_otp(data: LoginRequest):
    existing = OTP_STORE.get(data.email)

    if existing and datetime.utcnow() < existing["expiry"]:
        raise HTTPException(
            status_code=429,
            detail="OTP already sent. Please wait."
        )

    otp = generate_otp()

    # 🔥 TEMP: simulate sending OTP
    print(f"📩 OTP for {data.email}: {otp}")

    OTP_STORE[data.email] = {
        "otp": otp,
        "expiry": datetime.utcnow() + timedelta(minutes=OTP_EXPIRY_MINUTES)
    }

    return {"message": "OTP sent successfully"}

@app.post("/verify-otp")
def verify_otp(data: VerifyRequest):
    record = OTP_STORE.get(data.email)

    if not record:
        raise HTTPException(status_code=400, detail="OTP not found")

    if datetime.utcnow() > record["expiry"]:
        raise HTTPException(status_code=400, detail="OTP expired")

    if data.otp != record["otp"]:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    del OTP_STORE[data.email]
    return {"message": "OTP verified"}

# ================== WEBSOCKET CHAT ==================
connections: Dict[WebSocket, str] = {}
messages = []

@app.websocket("/ws/chat")
async def chat_ws(websocket: WebSocket):
    user = websocket.query_params.get("user", "Unknown")

    await websocket.accept()
    connections[websocket] = user
    print(f"✅ WebSocket connected: {user}")

    try:
        while True:
            data = await websocket.receive_json()

            # 💬 TEXT MESSAGE
            if data["type"] == "message":
                msg = {
                    "id": str(uuid4()),
                    "type": "message",
                    "user": user,
                    "text": data["text"],
                    "reactions": {},
                }
                messages.append(msg)
                for ws in list(connections.keys()):
                    await ws.send_json(msg)

            # 🖼️ IMAGE MESSAGE
            elif data["type"] == "image":
                msg = {
                    "id": str(uuid4()),
                    "type": "image",
                    "user": user,
                    "image": data["image"],
                    "reactions": {},
                }
                messages.append(msg)
                for ws in list(connections.keys()):
                    await ws.send_json(msg)

            # ❤️ REACTION
            elif data["type"] == "reaction":
                for msg in messages:
                    if msg["id"] == data["messageId"]:
                        emoji = data["emoji"]
                        msg.setdefault("reactions", {})
                        msg["reactions"].setdefault(emoji, [])

                        if user not in msg["reactions"][emoji]:
                            msg["reactions"][emoji].append(user)

                        for ws in list(connections.keys()):
                            await ws.send_json({
                                "type": "reaction",
                                "messageId": msg["id"],
                                "reactions": msg["reactions"],
                            })

            # ✍️ TYPING
            elif data["type"] == "typing":
                for ws in list(connections.keys()):
                    if ws != websocket:
                        await ws.send_json({
                            "type": "typing",
                            "user": user
                        })

    except WebSocketDisconnect:
        connections.pop(websocket, None)
        print(f"❌ WebSocket disconnected: {user}")
