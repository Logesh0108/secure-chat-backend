from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
from typing import Dict
import random
import base64
import pickle
import os
import uuid
from email.message import EmailMessage
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from uuid import uuid4
from collections import defaultdict

from googleapiclient.discovery import build
from google.auth.transport.requests import Request

# ================== APP ==================
app = FastAPI()


@app.get("/")
def root():
    return {"status": "Secure Chat Backend Running 🚀"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://secure-chat-frontend.onrender.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================== CONFIG ==================
OTP_EXPIRY_MINUTES = 4
OTP_STORE: Dict[str, dict] = {}

SENDER_EMAIL = "logeshnalliyappan@gmail.com"

# ================== MODELS ==================
class LoginRequest(BaseModel):
    email: EmailStr

class VerifyRequest(BaseModel):
    email: EmailStr
    otp: str

# ================== OTP HELPERS ==================
def generate_otp() -> str:
    return str(random.randint(100000, 999999))

def get_gmail_service():
    if not os.path.exists("token.pickle"):
        raise Exception("token.pickle not found. Run gmail_auth.py first.")

    with open("token.pickle", "rb") as token:
        creds = pickle.load(token)

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())

    return build("gmail", "v1", credentials=creds)

def send_email_otp(to_email: str, otp: str):
    try:
        service = get_gmail_service()

        msg = EmailMessage()
        msg.set_content(
            f"""
Your Secure Chat OTP is: {otp}

Requested at: {datetime.utcnow().isoformat()}
Request ID: {uuid.uuid4()}

This OTP is valid for 4 minutes.
Do not share this OTP.
"""
        )

        msg["To"] = to_email
        msg["From"] = SENDER_EMAIL
        msg["Subject"] = "Secure Chat OTP"

        encoded_message = base64.urlsafe_b64encode(
            msg.as_bytes()
        ).decode()

        service.users().messages().send(
            userId="me",
            body={"raw": encoded_message}
        ).execute()

    except Exception as e:
        print("GMAIL API ERROR:", e)
        raise HTTPException(
            status_code=500,
            detail="Failed to send OTP email"
        )

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

    # send first
    send_email_otp(data.email, otp)

    # store only if send succeeded
    OTP_STORE[data.email] = {
        "otp": otp,
        "expiry": datetime.utcnow() + timedelta(minutes=OTP_EXPIRY_MINUTES)
    }

    return {"message": "OTP sent"}

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
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket, user: str):
        await websocket.accept()
        self.active_connections[websocket] = user

    def disconnect(self, websocket: WebSocket):
        self.active_connections.pop(websocket, None)

    async def broadcast_message(self, sender_ws: WebSocket, text: str):
        sender = self.active_connections.get(sender_ws, "Unknown")

        payload = {
            "type": "message",
            "user": sender,
            "text": text,
            "time": datetime.utcnow().isoformat()
        }

        for connection in self.active_connections:
            await connection.send_json(payload)

    async def broadcast_typing(self, sender_ws: WebSocket):
        sender = self.active_connections.get(sender_ws, "Unknown")

        for connection in self.active_connections:
            if connection != sender_ws:
                await connection.send_json({
                    "type": "typing",
                    "user": sender
                })

manager = ConnectionManager()
# ================== WEBSOCKET CHAT ==================
from collections import defaultdict
from uuid import uuid4

connections = {}   # websocket -> user
messages = []      # stored messages with reactions


@app.websocket("/ws/chat")
async def chat_ws(websocket: WebSocket):
    user = websocket.query_params.get("user", "Unknown")
    await websocket.accept()
    connections[websocket] = user
    print(f"✅ WebSocket connected: {user}")

    try:
        while True:
            data = await websocket.receive_json()
            print("📩 Received:", data)

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
                for ws in connections:
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
                for ws in connections:
                    await ws.send_json(msg)

            # ❤️ REACTION (UPDATE ONLY)
            elif data["type"] == "reaction":
                for msg in messages:
                    if msg["id"] == data["messageId"]:
                        emoji = data["emoji"]
                        msg.setdefault("reactions", {})
                        msg["reactions"].setdefault(emoji, [])

                        if user not in msg["reactions"][emoji]:
                            msg["reactions"][emoji].append(user)

                        payload = {
                            "type": "reaction",
                            "messageId": msg["id"],
                            "reactions": msg["reactions"],
                        }

                        for ws in connections:
                            await ws.send_json(payload)

            # ✍️ TYPING (NOT A MESSAGE)
            elif data["type"] == "typing":
                for ws in connections:
                    if ws != websocket:
                        await ws.send_json({
                            "type": "typing",
                            "user": user
                        })

    except WebSocketDisconnect:
        connections.pop(websocket, None)
        print(f"❌ WebSocket disconnected: {user}")
