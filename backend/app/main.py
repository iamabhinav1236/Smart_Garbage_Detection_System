import os
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base, SessionLocal
from app.utils.seed import seed_initial_data
from app.utils.logger import logger
from app.utils.security import get_current_user, user_from_token
from app.camera.camera_manager import camera_manager

# Import all routers
from app.routers import (
    auth, bins, stream, dashboard,
    analytics, alerts, email_settings, system_settings
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure directories exist
    os.makedirs(settings.SNAPSHOTS_DIR, exist_ok=True)
    os.makedirs(settings.LOGS_DIR, exist_ok=True)

    logger.info("Initializing database schema...")
    Base.metadata.create_all(bind=engine)

    # Seed initial data
    db = SessionLocal()
    try:
        seed_initial_data(db)
        # Initialize background camera workers
        camera_manager.initialize(db)
    finally:
        db.close()

    yield

    # Shutdown
    logger.info("Shutting down Smart Garbage Detection System...")
    camera_manager.shutdown()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
    description="AI-Based Real-Time Smart Dustbin Monitoring System with YOLOv8 & Dual-ROI"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers. Login is public; everything else requires a valid token.
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
protected = [Depends(get_current_user)]
for module in (bins, stream, dashboard, analytics, alerts, email_settings, system_settings):
    app.include_router(module.router, prefix=settings.API_V1_PREFIX, dependencies=protected)

@app.get("/")
def root():
    return {
        "system": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "operational",
        "api_docs": "/docs"
    }

# Real-time WebSocket for live telemetry & alerts
active_connections: list[WebSocket] = []

@app.websocket("/ws/live")
async def websocket_live_telemetry(websocket: WebSocket):
    db = SessionLocal()
    try:
        authorized = user_from_token(websocket.query_params.get("token"), db) is not None
    finally:
        db.close()
    if not authorized:
        await websocket.close(code=1008)
        return
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            telemetry_data = camera_manager.get_all_telemetry()
            payload = {
                "type": "telemetry",
                "bins": telemetry_data
            }
            await websocket.send_json(payload)
            await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        if websocket in active_connections:
            active_connections.remove(websocket)
    except Exception as e:
        if websocket in active_connections:
            active_connections.remove(websocket)
