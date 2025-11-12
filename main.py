# backend/main.py
from __future__ import annotations

import json
import time
from typing import Dict, Any, Optional, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ In-memory store
FILES: Dict[str, Dict[str, Any]] = {}

LOCK_TIMEOUT = 60 * 10  # 10 minutes


# ================================
# ✅ REST MODELS
# ================================
class FilePayload(BaseModel):
    name: str
    xml: Optional[str] = ""


class SavePayload(BaseModel):
    xml: str


# ================================
# ✅ REST ENDPOINTS (FIXED)
# ================================

@app.get("/files")
async def list_files():
    """Return list of file IDs"""
    return list(FILES.keys())


@app.post("/files")
async def create_file(payload: FilePayload):
    fid = payload.name.strip()

    if not fid:
        return JSONResponse({"error": "Name cannot be empty"}, status_code=400)

    if fid in FILES:
        return JSONResponse({"error": "File already exists"}, status_code=409)

    FILES[fid] = {
        "xml": payload.xml or "",
        "lock": None,
        "users": set(),
        "focus": {},
        "sockets": set(),
    }
    return {"ok": True, "id": fid}


@app.get("/files/{file_id}")
async def get_file(file_id: str):
    room = FILES.get(file_id)
    if not room:
        return JSONResponse({"error": "File not found"}, status_code=404)

    return {"id": file_id, "xml": room["xml"], "lock": room["lock"]}


@app.put("/files/{file_id}")
async def save_file(file_id: str, payload: SavePayload):
    room = FILES.get(file_id)
    if not room:
        return JSONResponse({"error": "File not found"}, status_code=404)

    room["xml"] = payload.xml
    return {"ok": True}


# ================================
# ✅ Helper Broadcast Functions
# ================================

async def broadcast(file_id: str, message: Dict[str, Any]):
    room = FILES.get(file_id)
    if not room:
        return

    text = json.dumps(message)
    dead_sockets = []

    for ws in room["sockets"]:
        try:
            await ws.send_text(text)
        except Exception:
            dead_sockets.append(ws)

    # cleanup dead sockets
    for ws in dead_sockets:
        room["sockets"].discard(ws)


async def push_state(file_id: str):
    room = FILES.get(file_id)
    if not room:
        return

    await broadcast(file_id, {
        "type": "state",
        "xml": room["xml"],
        "lock": room["lock"],
        "users": list(room["users"]),
        "focus": room["focus"],
    })


# ================================
# ✅ WebSocket Endpoint
# ================================

@app.websocket("/ws/{file_id}")
async def websocket_endpoint(websocket: WebSocket, file_id: str):
    await websocket.accept()

    # ensure room exists
    if file_id not in FILES:
        FILES[file_id] = {
            "xml": "",
            "lock": None,
            "users": set(),
            "focus": {},
            "sockets": set(),
        }

    room = FILES[file_id]
    room["sockets"].add(websocket)
    username = None

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            op = data.get("type")

            if op == "join":
                username = data.get("user") or "anon"
                room["users"].add(username)
                await push_state(file_id)

            elif op == "lock":
                now = time.time()
                current_lock = room["lock"]

                if current_lock and (now - current_lock["since"] > LOCK_TIMEOUT):
                    room["lock"] = None

                if room["lock"] is None:
                    room["lock"] = {"by": username, "since": now}
                    await broadcast(file_id, {"type": "lock", "by": username})
                    await push_state(file_id)
                else:
                    await websocket.send_text(json.dumps({
                        "type": "lock-denied",
                        "lock": room["lock"],
                    }))

            elif op == "unlock":
                if room["lock"] and room["lock"]["by"] == username:
                    room["lock"] = None
                    await broadcast(file_id, {"type": "unlock"})
                    await push_state(file_id)

            elif op == "xml":
                if room["lock"] and room["lock"]["by"] == username:
                    room["xml"] = data["xml"]
                    await broadcast(file_id, {
                        "type": "xml",
                        "xml": room["xml"],
                        "by": username
                    })
                    await push_state(file_id)

            elif op == "focus":
                elem = data.get("element")
                if elem:
                    room["focus"][elem] = username
                    await push_state(file_id)

            elif op == "blur":
                elem = data.get("element")
                if elem in room["focus"]:
                    del room["focus"][elem]
                    await push_state(file_id)

    except WebSocketDisconnect:
        pass

    finally:
        room["sockets"].discard(websocket)
        if username in room["users"]:
            room["users"].remove(username)

        if room["lock"] and room["lock"]["by"] == username:
            room["lock"] = None

        await push_state(file_id)
