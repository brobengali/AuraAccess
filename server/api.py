"""
FastAPI Backend Server & Local WebSocket Streamer
Provides REST APIs for multi-user profiles, live WebSocket telemetry,
and live local /video_feed stream for visual feedback.
Bound strictly to 127.0.0.1 (Localhost only) for zero-cloud security.
"""

import os
import asyncio
from pathlib import Path
from typing import List, Dict, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse, Response
from pydantic import BaseModel

from server.profile_store import UserProfileData

IS_VERCEL = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))

app = FastAPI(title="Hands-Free Accessibility System", version="2.0.0")

# Initialize engine: hardware desktop engine for local PC, CloudDemoEngine for Vercel/serverless
if not IS_VERCEL:
    try:
        from server.state import TrackingEngineService
        engine = TrackingEngineService()
        engine.start_background_service()
    except Exception:
        from server.cloud_engine import CloudDemoEngine
        engine = CloudDemoEngine()
else:
    from server.cloud_engine import CloudDemoEngine
    engine = CloudDemoEngine()

# Static directory setup
web_dir = Path(__file__).resolve().parent.parent / "web"
try:
    web_dir.mkdir(parents=True, exist_ok=True)
except Exception:
    pass


class ToggleTrackingRequest(BaseModel):
    enabled: bool


class CreateProfileRequest(BaseModel):
    name: str


class SensitivityRequest(BaseModel):
    sensitivity: float


class EngagementUpdateRequest(BaseModel):
    mode: str
    hotkey: str


class ArmRequest(BaseModel):
    armed: bool


@app.get("/", response_class=HTMLResponse)
def serve_index():
    index_file = web_dir / "index.html"
    if index_file.exists():
        content = index_file.read_text(encoding="utf-8")
        return HTMLResponse(content=content)
    return HTMLResponse("<h1>Hands-Free Accessibility API is running. UI files not found.</h1>")


def generate_camera_stream():
    """Streams live annotated frames as MJPEG multipart stream directly to <img> in UI."""
    import time
    while True:
        with engine._lock:
            frame_bytes = engine.latest_jpeg_bytes
        if frame_bytes is not None:
            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")
        time.sleep(0.04)


@app.get("/video_feed")
def video_feed():
    """Live camera video feed endpoint."""
    if IS_VERCEL:
        return Response(status_code=204)

    return StreamingResponse(
        generate_camera_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.get("/api/profiles", response_model=List[UserProfileData])
def list_profiles():
    return engine.profile_store.list_profiles()


@app.post("/api/profiles", response_model=UserProfileData)
def create_profile(req: CreateProfileRequest):
    new_id = req.name.strip().lower().replace(" ", "_")
    profile = UserProfileData(
        id=new_id,
        name=req.name.strip(),
        calibrated=False
    )
    saved = engine.profile_store.save_profile(profile)
    engine.set_active_profile(saved.id)
    return saved


@app.post("/api/profiles/active/{profile_id}")
def set_active_profile(profile_id: str):
    success = engine.set_active_profile(profile_id)
    if not success:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"status": "success", "active_profile_id": profile_id}


@app.put("/api/profiles/{profile_id}", response_model=UserProfileData)
def update_profile(profile_id: str, profile_data: UserProfileData):
    if profile_id != profile_data.id:
        raise HTTPException(status_code=400, detail="ID mismatch")
    saved = engine.profile_store.save_profile(profile_data)
    if engine.active_profile.id == profile_id:
        engine.set_active_profile(profile_id)
    return saved


@app.delete("/api/profiles/{profile_id}")
def delete_profile(profile_id: str):
    if len(engine.profile_store.list_profiles()) <= 1:
        raise HTTPException(status_code=400, detail="Cannot delete the only remaining profile")
    success = engine.profile_store.delete_profile(profile_id)
    if not success:
        raise HTTPException(status_code=404, detail="Profile not found")
    remaining = engine.profile_store.list_profiles()
    engine.set_active_profile(remaining[0].id)
    return {"status": "success"}


@app.post("/api/tracking/toggle")
def toggle_tracking(req: ToggleTrackingRequest):
    active = engine.toggle_tracking(req.enabled)
    return {"status": "success", "tracking_enabled": active}


@app.post("/api/sensitivity")
def update_sensitivity(req: SensitivityRequest):
    engine.set_sensitivity(req.sensitivity)
    return {"status": "success", "sensitivity": engine.sensitivity_multiplier}


@app.post("/api/engagement")
def set_engagement(req: EngagementUpdateRequest):
    engine.set_engagement_config(req.mode, req.hotkey)
    return {"status": "success", "mode": engine.engagement_mode, "hotkey": engine.engagement_hotkey}


@app.post("/api/engagement/arm")
def set_arm(req: ArmRequest):
    armed = engine.set_software_arm(req.armed)
    return {"status": "success", "engaged": armed}


@app.get("/api/status")
def get_status():
    return engine.latest_telemetry


@app.websocket("/ws/telemetry")
async def websocket_telemetry(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = dict(engine.latest_telemetry)
            await websocket.send_json(data)
            await asyncio.sleep(0.04)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass


# Mount static assets
app.mount("/static", StaticFiles(directory=str(web_dir)), name="static")
