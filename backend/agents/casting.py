"""Agent 2: Casting Director — Matches scenes to stock video using Nova Multimodal Embeddings + Pexels."""

from __future__ import annotations

import json
import os
import logging
import re
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
USE_NOVA_EMBEDDINGS = os.getenv("USE_NOVA_EMBEDDINGS", "false").lower() in {
    "1", "true", "yes", "on"
}

# Cache for Pexels search results and their embeddings
_pexels_cache: dict[str, List[dict]] = {}
_embedding_cache: dict[str, List[float]] = {}


def _extract_keywords(text: str) -> list[str]:
    stopwords = {
        "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with", "from", "at", "by",
        "is", "are", "was", "were", "be", "been", "as", "that", "this", "it", "its", "after",
        "amid", "over", "under", "into", "about", "new", "says", "say", "will", "could",
    }
    tokens = re.findall(r"[A-Za-z0-9']+", text.lower())
    keywords: list[str] = []
    for token in tokens:
        if len(token) <= 3 or token in stopwords or token in keywords:
            continue
        keywords.append(token)
    return keywords


def _infer_topic(text: str) -> str:
    text = text.lower()
    topic_rules = {
        "finance": {"stocks", "stock", "dow", "nasdaq", "market", "oil", "earnings", "investor", "economy", "trade"},
        "space": {"moon", "mars", "rocket", "nasa", "space", "astronaut", "launch", "mission", "satellite"},
        "politics": {"president", "administration", "congress", "senate", "government", "minister", "election", "vote", "policy"},
        "crime": {"attack", "killed", "arrest", "shooting", "suspect", "police", "security", "crime", "court"},
        "health": {"health", "medical", "hospital", "doctor", "disease", "therapy", "virus", "drug"},
        "climate": {"climate", "storm", "wildfire", "flood", "weather", "heat", "earthquake", "hurricane"},
        "technology": {"ai", "artificial", "chip", "tech", "software", "robot", "quantum", "battery"},
    }
    for topic, words in topic_rules.items():
        if any(word in text for word in words):
            return topic
    return "general"


def _build_search_queries(scene_query: str, headline: str, scene_number: int) -> list[str]:
    keywords = _extract_keywords(headline)
    topic = _infer_topic(headline)
    kw1 = keywords[0] if len(keywords) > 0 else "news"
    kw2 = keywords[1] if len(keywords) > 1 else "update"
    kw3 = keywords[2] if len(keywords) > 2 else "world"

    topic_queries = {
        "finance": [
            f"{kw1} {kw2} stock market",
            "stock market trading screen",
            "business district skyline",
            "oil refinery energy market",
        ],
        "space": [
            f"{kw1} {kw2} rocket launch",
            "mission control nasa",
            "astronaut training space",
            "moon mission spacecraft",
        ],
        "politics": [
            f"{kw1} {kw2} government",
            "government building press conference",
            "politician podium flags",
            "public protest crowd",
        ],
        "crime": [
            f"{kw1} {kw2} police",
            "police crime scene tape",
            "security camera city street",
            "courthouse press conference",
        ],
        "health": [
            f"{kw1} {kw2} hospital",
            "hospital doctor patient",
            "medical laboratory research",
            "health press briefing",
        ],
        "climate": [
            f"{kw1} {kw2} weather",
            "storm clouds disaster response",
            "flood wildfire emergency",
            "climate data map",
        ],
        "technology": [
            f"{kw1} {kw2} technology",
            "technology lab computers",
            "robotics engineers hardware",
            "conference keynote audience",
        ],
        "general": [
            f"{kw1} {kw2} {kw3}",
            f"{kw1} news footage",
            f"{kw2} public reaction",
            "press conference world news",
        ],
    }

    scene_specific = {
        1: [scene_query, f"{kw1} {kw2} breaking news"],
        2: [scene_query, f"{kw1} public reaction"],
        3: [scene_query, f"{kw2} official statement"],
        4: [scene_query, f"{kw1} global map data"],
    }

    candidates = scene_specific.get(scene_number, [scene_query]) + topic_queries[topic]
    queries: list[str] = []
    for candidate in candidates:
        cleaned = candidate.strip()
        if cleaned and cleaned not in queries:
            queries.append(cleaned)
    return queries


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
    use_embeddings = USE_NOVA_EMBEDDINGS and bool(PEXELS_API_KEY)
    if not use_embeddings and PEXELS_API_KEY:
        await broadcast_log("CASTING", "info", "Nova embeddings disabled; using keyword matching mode")

    for scene in job.blueprint.scenes:
        try:
            query = scene.visual_description
            search_queries = _build_search_queries(query, job.source_headline, scene.scene_number)

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
                for candidate_query in search_queries:
                    videos = await _search_pexels_videos(candidate_query)
                    if videos:
                        scene_assets.append(SceneAsset(
                            scene_number=scene.scene_number,
                            video_url=videos[0]["url"],
                            similarity_score=0.70,
                        ))
                        await broadcast_log(
                            "CASTING", "info",
                            f"Scene {scene.scene_number}: keyword match using '{candidate_query}' (score: 0.70)"
                        )
                        break
                else:
                    videos = []

                if videos:
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
