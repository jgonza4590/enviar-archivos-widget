from fastapi import FastAPI, File, UploadFile, Form, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import shutil
import os
import uuid
from datetime import datetime

app = FastAPI(title="Widget Envío de Archivos - FastAPI")

# Permitir CORS por si accedes desde otra IP en la misma red
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servir archivos estáticos y subidas
app.mount("/static", StaticFiles(directory="../frontend/static"), name="static")
app.mount("/uploads", StaticFiles(directory="../uploads"), name="uploads")

# Base de datos simulada en memoria (para la clase es perfecto y rápido)
messages_db = []

# --- Gestor de WebSockets para comunicación en tiempo real ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass

manager = ConnectionManager()

# --- Rutas de la Interfaz (Frontend) ---
@app.get("/")
async def get_mobile_ui():
    """Sirve la interfaz del móvil."""
    file_path = os.path.join(os.path.dirname(__file__), "../frontend/index.html")
    with open(file_path, "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.get("/pc")
async def get_pc_ui():
    """Sirve la interfaz del PC."""
    file_path = os.path.join(os.path.dirname(__file__), "../frontend/pc-widget.html")
    with open(file_path, "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

# --- Rutas de la API (Backend) ---
@app.post("/api/messages")
async def send_message(
    source: str = Form(...),
    text: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None)
):
    """Recibe un mensaje con o sin archivo."""
    if not text and not file:
        raise HTTPException(status_code=400, detail="Debe enviar texto o un archivo.")

    msg_id = str(uuid.uuid4())
    file_url = None
    file_name = None
    file_type = None

    if file:
        # Guardar archivo físicamente
        file_name = file.filename
        file_type = file.content_type
        # Nombre único para evitar sobrescribir
        safe_name = f"{msg_id}_{file_name}"
        save_path = os.path.join("../uploads", safe_name)
        
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        file_url = f"/uploads/{safe_name}"

    new_msg = {
        "id": msg_id,
        "source": source, # 'mobile' o 'pc'
        "text": text,
        "image_url": file_url,
        "file_name": file_name,
        "file_type": file_type,
        "created_at": datetime.now().isoformat()
    }
    
    # Añadir a nuestra "base de datos"
    messages_db.insert(0, new_msg)

    # Avisar a todos los clientes (móvil y PC) que hay un nuevo mensaje
    await manager.broadcast("NEW_MESSAGE")

    return {"status": "ok", "message": "Enviado con éxito", "data": new_msg}

@app.get("/api/messages")
async def get_messages(source_filter: Optional[str] = None):
    """Devuelve los mensajes. Opcionalmente filtra por origen."""
    if source_filter:
        filtered = [m for m in messages_db if m["source"] == source_filter]
        return filtered
    return messages_db

@app.delete("/api/messages")
async def clear_messages():
    """Borra todos los mensajes y archivos."""
    messages_db.clear()
    
    # Limpiar carpeta de uploads (excepto archivos ocultos como .gitkeep)
    uploads_dir = "../uploads"
    for filename in os.listdir(uploads_dir):
        file_path = os.path.join(uploads_dir, filename)
        if os.path.isfile(file_path):
            os.unlink(file_path)

    await manager.broadcast("MESSAGES_CLEARED")
    return {"status": "ok", "message": "Historial y archivos borrados"}

# --- Endpoint de WebSockets ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Punto de conexión para recibir notificaciones en tiempo real."""
    await manager.connect(websocket)
    try:
        while True:
            # Mantener conexión viva. El cliente puede enviar 'ping'
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
