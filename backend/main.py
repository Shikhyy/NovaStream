"""NovaStream 24/7 — FastAPI backend with WebSocket server."""

from __future__ import annotations

import asyncio
import os
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from models import EpisodeStatus
from broadcaster import manager
from pipeline import run_pipeline_loop, episode_queue, current_episode, pipeline_running

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("novastream")

_pipeline_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start the pipeline loop on app startup."""
    global _pipeline_task
    logger.info("NovaStream 24/7 starting up...")

    # Ensure episode output directory exists
    Path("/tmp/novastream/episodes").mkdir(parents=True, exist_ok=True)

    # Start the pipeline loop
    _pipeline_task = asyncio.create_task(run_pipeline_loop())
    yield

    # Shutdown
    logger.info("Shutting down pipeline...")
    if _pipeline_task:
        _pipeline_task.cancel()
        try:
            await _pipeline_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="NovaStream 24/7",
    description="Autonomous AI-powered television network",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve episode video files
episodes_dir = Path("/tmp/novastream/episodes")
episodes_dir.mkdir(parents=True, exist_ok=True)
app.mount("/episodes", StaticFiles(directory=str(episodes_dir)), name="episodes")


# --- REST Endpoints ---

@app.get("/health")
async def health():
    return {
        "status": "online",
        "pipeline_running": pipeline_running,
        "episodes_count": manager.episodes_count,
        "queue_length": len(episode_queue),
        "uptime_secs": int(__import__("time").time() - manager.start_time),
    }


@app.get("/api/episodes")
async def list_episodes():
    """List the last 20 completed episodes."""
    completed = [
        job.model_dump()
        for job in reversed(episode_queue)
        if job.status in (EpisodeStatus.READY, EpisodeStatus.LIVE)
    ][:20]
    return {"episodes": completed}


@app.get("/api/episodes/{episode_id}")
async def get_episode(episode_id: str):
    """Get details for a specific episode."""
    for job in episode_queue:
        if job.episode_id == episode_id:
            return job.model_dump()
    return JSONResponse(status_code=404, content={"error": "Episode not found"})


@app.post("/api/skip")
async def skip_episode():
    """Skip the current episode and advance the queue."""
    if current_episode:
        current_episode.status = EpisodeStatus.FAILED
        current_episode.error_log.append("Skipped by admin")
        return {"status": "skipped", "episode_id": current_episode.episode_id}
    return {"status": "no_active_episode"}


# --- WebSocket ---

@app.websocket("/ws/broadcast")
async def websocket_broadcast(websocket: WebSocket):
    """WebSocket endpoint for real-time frontend updates."""
    await manager.connect(websocket)
    logger.info(f"WebSocket client connected ({len(manager.connections)} total)")

    try:
        # Send current state on connect
        if episode_queue:
            await manager.broadcast_queue(episode_queue[-10:])
        if current_episode and current_episode.video_url:
            await manager.broadcast_now_playing(current_episode)
        await manager.broadcast_stats()

        # Keep connection alive
        while True:
            data = await websocket.receive_text()
            # Client can send ping/pong or commands
            if data == "ping":
                await websocket.send_text('{"type":"pong"}')
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info(f"WebSocket client disconnected ({len(manager.connections)} total)")
    except Exception:
        manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=False,
    )
