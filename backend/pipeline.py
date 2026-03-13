"""Master pipeline loop — orchestrates all 4 agents in sequence."""

from __future__ import annotations

import asyncio
import time
import logging
from datetime import datetime
from typing import List

from models import EpisodeJob, EpisodeStatus
from news import fetch_headline
from agents.showrunner import run_showrunner
from agents.casting import run_casting
from agents.voice import run_voice
from agents.editor import run_editor
from broadcaster import manager

logger = logging.getLogger("novastream.pipeline")

# Episode queue shared with the API
episode_queue: List[EpisodeJob] = []
current_episode: EpisodeJob | None = None
pipeline_running = False


async def broadcast_log(agent_id: str, level: str, message: str):
    """Helper to log + broadcast."""
    prefix = {"info": "ℹ", "success": "✓", "warn": "⚠", "error": "✗"}.get(level, "•")
    logger.info(f"[{agent_id}] {prefix} {message}")
    await manager.broadcast_log(agent_id, level, message)


async def produce_episode() -> EpisodeJob:
    """Run the full pipeline for a single episode."""
    global current_episode

    # Step 0: Fetch headline
    headline = await fetch_headline()
    job = EpisodeJob(source_headline=headline)
    current_episode = job
    episode_queue.append(job)

    await broadcast_log("PIPELINE", "info", f"═══ Episode {job.episode_id} started ═══")
    await broadcast_log("PIPELINE", "info", f"Headline: {headline}")
    await manager.broadcast_queue(episode_queue[-10:])  # Keep last 10

    start_time = time.time()

    # Step 1: Showrunner (Agent 1 — Nova 2 Lite)
    job = await run_showrunner(job, broadcast_log)
    await manager.broadcast_queue(episode_queue[-10:])

    if not job.blueprint:
        job.status = EpisodeStatus.FAILED
        await broadcast_log("PIPELINE", "error", "Pipeline aborted: no blueprint")
        return job

    # Step 2 & 3: Casting + Voice in parallel (Agents 2 & 3)
    await broadcast_log("PIPELINE", "info", "Running Casting + Voice agents in parallel...")
    job_casting, job_voice = await asyncio.gather(
        run_casting(job, broadcast_log),
        run_voice(job, broadcast_log),
    )

    # Merge results (both modify the same job object but different fields)
    job.scene_assets = job_casting.scene_assets
    job.audio_files = job_voice.audio_files
    await manager.broadcast_queue(episode_queue[-10:])

    # Update embedding score stat
    if job.scene_assets:
        manager.embed_score_avg = sum(a.similarity_score for a in job.scene_assets) / len(job.scene_assets)

    # Step 4: Editor (Agent 4 — FFmpeg)
    job = await run_editor(job, broadcast_log)
    await manager.broadcast_queue(episode_queue[-10:])

    if job.status != EpisodeStatus.FAILED:
        job.status = EpisodeStatus.READY
        job.completed_at = datetime.utcnow()
        elapsed = time.time() - start_time
        manager.episodes_count += 1

        await broadcast_log("PIPELINE", "success",
            f"═══ Episode {job.episode_id} complete ({elapsed:.1f}s) ═══")
    else:
        await broadcast_log("PIPELINE", "error", f"Episode {job.episode_id} failed")

    return job


async def run_pipeline_loop():
    """Continuously produce episodes. Never stops."""
    global pipeline_running
    pipeline_running = True

    await broadcast_log("PIPELINE", "info", "🚀 NovaStream pipeline starting...")
    await manager.start_stats_loop()

    while pipeline_running:
        try:
            job = await produce_episode()

            if job.status == EpisodeStatus.READY and job.video_url:
                job.status = EpisodeStatus.LIVE
                await manager.broadcast_now_playing(job)
                await manager.broadcast_queue(episode_queue[-10:])

                # Wait for approximate episode duration before starting next
                total_duration = sum(
                    s.duration_seconds for s in (job.blueprint.scenes if job.blueprint else [])
                )
                await broadcast_log("PIPELINE", "info",
                    f"Broadcasting episode {job.episode_id} ({total_duration}s). Next in {total_duration + 5}s...")
                await asyncio.sleep(max(total_duration, 30) + 5)
            else:
                # On failure, wait a bit then try next headline
                await asyncio.sleep(10)

        except asyncio.CancelledError:
            break
        except Exception as e:
            await broadcast_log("PIPELINE", "error", f"Pipeline loop error: {e}")
            await asyncio.sleep(15)

    pipeline_running = False
    manager.stop_stats_loop()
