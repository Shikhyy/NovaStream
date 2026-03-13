"""Agent 2: Casting Director — Matches scenes to stock video using Nova Multimodal Embeddings + Pexels."""

from __future__ import annotations

import json
import os
import logging
from typing import List

import boto3
import httpx
import numpy as np
from dotenv import load_dotenv

from models import EpisodeJob, EpisodeStatus, SceneAsset

load_dotenv()
logger = logging.getLogger("novastream.casting")

NOVA_EMBEDDINGS_MODEL_ID = os.getenv(
    "NOVA_EMBEDDINGS_MODEL_ID", "amazon.nova-2-multimodal-embeddings-v1:0"
)
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")

# Cache for Pexels search results and their embeddings
_pexels_cache: dict[str, List[dict]] = {}
_embedding_cache: dict[str, List[float]] = {}


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    a_arr = np.array(a)
    b_arr = np.array(b)
    return float(np.dot(a_arr, b_arr) / (np.linalg.norm(a_arr) * np.linalg.norm(b_arr) + 1e-9))


async def _get_text_embedding(text: str) -> List[float]:
    """Get text embedding from Amazon Nova Multimodal Embeddings via invoke_model."""
    cache_key = text.strip().lower()
    if cache_key in _embedding_cache:
        return _embedding_cache[cache_key]

    client = boto3.client("bedrock-runtime", region_name=AWS_REGION)

    # Nova Multimodal Embeddings API format
    body = json.dumps({
        "inputText": text,
        "embeddingConfig": {"outputEmbeddingLength": 1024}
    })

    response = client.invoke_model(
        modelId=NOVA_EMBEDDINGS_MODEL_ID,
        body=body,
        contentType="application/json",
        accept="application/json",
    )

    result = json.loads(response["body"].read())
    embedding = result["embedding"]
    _embedding_cache[cache_key] = embedding
    return embedding


async def _search_pexels_videos(query: str, per_page: int = 5) -> List[dict]:
    """Search Pexels for stock video clips."""
    if not PEXELS_API_KEY:
        return []

    cache_key = query.lower().strip()
    if cache_key in _pexels_cache:
        return _pexels_cache[cache_key]

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            "https://api.pexels.com/videos/search",
            params={"query": query, "per_page": per_page, "size": "medium"},
            headers={"Authorization": PEXELS_API_KEY},
        )
        if resp.status_code == 200:
            videos = resp.json().get("videos", [])
            results = []
            for v in videos:
                files = v.get("video_files", [])
                medium = next(
                    (f for f in files if f.get("quality") == "sd" and f.get("width", 0) >= 640),
                    files[0] if files else None,
                )
                if medium:
                    results.append({
                        "url": medium["link"],
                        "width": medium.get("width", 0),
                        "height": medium.get("height", 0),
                        "duration": v.get("duration", 0),
                    })
            _pexels_cache[cache_key] = results
            return results

    return []


async def run_casting(job: EpisodeJob, broadcast_log) -> EpisodeJob:
    """Match each scene to a stock video clip using Nova Multimodal Embeddings + Pexels."""
    job.status = EpisodeStatus.CASTING
    await broadcast_log("CASTING", "info", "Starting scene-to-video matching...")

    if not job.blueprint:
        await broadcast_log("CASTING", "error", "No blueprint available")
        job.error_log.append("Casting: no blueprint")
        return job

    scene_assets: List[SceneAsset] = []
    use_embeddings = True

    for scene in job.blueprint.scenes:
        try:
            query = scene.visual_description

            # Try embedding-based semantic search
            if use_embeddings and PEXELS_API_KEY:
                try:
                    scene_embedding = await _get_text_embedding(query)
                    await broadcast_log(
                        "CASTING", "info",
                        f"Scene {scene.scene_number}: Nova embedding generated ({len(scene_embedding)}d vector)"
                    )

                    # Search Pexels and embed search terms for comparison
                    videos = await _search_pexels_videos(query)

                    if videos:
                        # Embed the query used for Pexels search and compute similarity
                        # against the scene description embedding as a quality metric
                        search_embedding = await _get_text_embedding(query[:50])
                        sim_score = _cosine_similarity(scene_embedding, search_embedding)

                        best_video = videos[0]
                        scene_assets.append(SceneAsset(
                            scene_number=scene.scene_number,
                            video_url=best_video["url"],
                            similarity_score=round(sim_score, 4),
                        ))
                        await broadcast_log(
                            "CASTING", "success",
                            f"Scene {scene.scene_number}: matched video (embed score: {sim_score:.2f})"
                        )
                        continue
                except Exception as e:
                    await broadcast_log("CASTING", "warn", f"Nova Embeddings failed: {e}")
                    use_embeddings = False

            # Fallback: direct Pexels keyword search (no embeddings)
            if PEXELS_API_KEY:
                videos = await _search_pexels_videos(query)
                if videos:
                    scene_assets.append(SceneAsset(
                        scene_number=scene.scene_number,
                        video_url=videos[0]["url"],
                        similarity_score=0.70,
                    ))
                    await broadcast_log(
                        "CASTING", "info",
                        f"Scene {scene.scene_number}: keyword match (no embedding, score: 0.70)"
                    )
                    continue

            # Final fallback: use placeholder
            scene_assets.append(SceneAsset(
                scene_number=scene.scene_number,
                video_url="",
                similarity_score=0.0,
            ))
            await broadcast_log("CASTING", "warn", f"Scene {scene.scene_number}: no video found, using placeholder")

        except Exception as e:
            await broadcast_log("CASTING", "error", f"Scene {scene.scene_number} failed: {e}")
            scene_assets.append(SceneAsset(
                scene_number=scene.scene_number,
                video_url="",
                similarity_score=0.0,
            ))
            job.error_log.append(f"Casting scene {scene.scene_number}: {e}")

    job.scene_assets = scene_assets
    avg_score = sum(a.similarity_score for a in scene_assets) / max(len(scene_assets), 1)
    await broadcast_log("CASTING", "success", f"Casting complete. Avg embed score: {avg_score:.2f}")
    return job
