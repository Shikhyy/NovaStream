"""Pydantic data models for NovaStream 24/7."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional, Literal

from pydantic import BaseModel, Field


# --- Blueprint models (Agent 1 output) ---

class Scene(BaseModel):
    scene_number: int = Field(ge=1, le=4)
    visual_description: str = Field(max_length=120)
    voiceover_script: str  # max 60 words enforced in prompt
    duration_seconds: int = Field(ge=10, le=20)


class Blueprint(BaseModel):
    title: str = Field(max_length=80)
    tone: Literal["dramatic", "satirical", "documentary"]
    scenes: List[Scene] = Field(min_length=1, max_length=4)


# --- Asset models (Agent 2 & 3 output) ---

class SceneAsset(BaseModel):
    scene_number: int
    video_url: str
    similarity_score: float = 0.0


# --- Episode state ---

class EpisodeStatus(str, Enum):
    QUEUED = "queued"
    SCRIPTING = "scripting"
    CASTING = "casting"
    VOICING = "voicing"
    EDITING = "editing"
    READY = "ready"
    LIVE = "live"
    FAILED = "failed"


class EpisodeJob(BaseModel):
    episode_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    status: EpisodeStatus = EpisodeStatus.QUEUED
    source_headline: str = ""
    blueprint: Optional[Blueprint] = None
    scene_assets: List[SceneAsset] = Field(default_factory=list)
    audio_files: List[str] = Field(default_factory=list)
    video_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error_log: List[str] = Field(default_factory=list)


# --- WebSocket message types ---

class WSMessageType(str, Enum):
    LOG_LINE = "LOG_LINE"
    QUEUE_UPDATE = "QUEUE_UPDATE"
    NOW_PLAYING = "NOW_PLAYING"
    SYSTEM_STATS = "SYSTEM_STATS"
