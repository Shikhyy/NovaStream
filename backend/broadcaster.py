"""WebSocket broadcast manager and connection handler."""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime
from typing import List, Dict, Any

from fastapi import WebSocket
from models import EpisodeJob, WSMessageType


class BroadcastManager:
    """Manages WebSocket connections and broadcasts messages to all connected clients."""

    def __init__(self):
        self.connections: List[WebSocket] = []
        self.start_time = time.time()
        self.episodes_count = 0
        self.last_sonic_latency = 0.0
        self.embed_score_avg = 0.0
        self._stats_task: asyncio.Task | None = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.connections:
            self.connections.remove(websocket)

    async def broadcast(self, message: dict):
        """Send message to all connected WebSocket clients."""
        dead = []
        data = json.dumps(message, default=str)
        for ws in self.connections:
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    async def broadcast_log(self, agent_id: str, level: str, message: str):
        """Broadcast a log line to all connected clients."""
        await self.broadcast({
            "type": WSMessageType.LOG_LINE,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "agent_id": agent_id,
            "level": level,
            "message": message,
        })

    async def broadcast_queue(self, queue: List[EpisodeJob]):
        """Broadcast the current episode queue state."""
        await self.broadcast({
            "type": WSMessageType.QUEUE_UPDATE,
            "queue": [job.model_dump() for job in queue],
        })

    async def broadcast_now_playing(self, job: EpisodeJob):
        """Broadcast the currently playing episode."""
        await self.broadcast({
            "type": WSMessageType.NOW_PLAYING,
            "video_url": job.video_url,
            "episode_id": job.episode_id,
            "title": job.blueprint.title if job.blueprint else "",
            "headline": job.source_headline,
        })

    async def broadcast_stats(self):
        """Broadcast system statistics."""
        await self.broadcast({
            "type": WSMessageType.SYSTEM_STATS,
            "uptime_secs": int(time.time() - self.start_time),
            "episodes_count": self.episodes_count,
            "sonic_latency_ms": self.last_sonic_latency,
            "embed_score_avg": round(self.embed_score_avg, 2),
        })

    async def start_stats_loop(self):
        """Start broadcasting stats every 5 seconds."""
        async def _loop():
            while True:
                await self.broadcast_stats()
                await asyncio.sleep(5)
        self._stats_task = asyncio.create_task(_loop())

    def stop_stats_loop(self):
        if self._stats_task:
            self._stats_task.cancel()


# Singleton instance
manager = BroadcastManager()
