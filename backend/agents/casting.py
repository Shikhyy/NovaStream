"""Agent 2: Casting Director — Matches scenes to stock video using smart Pexels ranking."""

from __future__ import annotations

import os
import logging
import re
from typing import List

import httpx
from dotenv import load_dotenv

from models import EpisodeJob, EpisodeStatus, SceneAsset

load_dotenv()
logger = logging.getLogger("novastream.casting")

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")

# Cache for Pexels search results (capped to limit memory)
_pexels_cache: dict[str, List[dict]] = {}
_PEXELS_CACHE_MAX = 30


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


def _tokenize(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9']+", text.lower()) if len(t) > 2}


def _query_relevance_score(scene_query: str, candidate_query: str, headline: str) -> float:
    scene_tokens = _tokenize(scene_query)
    headline_tokens = _tokenize(headline)
    candidate_tokens = _tokenize(candidate_query)
    if not candidate_tokens:
        return 0.0

    scene_overlap = len(scene_tokens & candidate_tokens) / max(len(candidate_tokens), 1)
    headline_overlap = len(headline_tokens & candidate_tokens) / max(len(candidate_tokens), 1)
    return min(1.0, (0.7 * scene_overlap) + (0.3 * headline_overlap))


def _video_quality_score(video: dict, target_duration: int) -> float:
    width = int(video.get("width", 0) or 0)
    height = int(video.get("height", 0) or 0)
    duration = int(video.get("duration", 0) or 0)

    if width <= 0 or height <= 0:
        resolution_score = 0.0
        aspect_score = 0.0
    else:
        resolution_score = min(1.0, (width * height) / float(1920 * 1080))
        aspect_ratio = width / max(height, 1)
        aspect_delta = abs(aspect_ratio - (16 / 9))
        aspect_score = max(0.0, 1.0 - (aspect_delta / 1.2))

    if duration <= 0:
        duration_score = 0.5
    else:
        delta = abs(duration - target_duration)
        duration_score = max(0.0, 1.0 - (delta / max(target_duration, 1)))

    return (0.5 * resolution_score) + (0.2 * aspect_score) + (0.3 * duration_score)


def _ranked_video_score(
    *,
    scene_query: str,
    candidate_query: str,
    headline: str,
    target_duration: int,
    video: dict,
    already_used: bool,
) -> float:
    query_score = _query_relevance_score(scene_query, candidate_query, headline)
    quality_score = _video_quality_score(video, target_duration)
    duplicate_penalty = 0.25 if already_used else 0.0
    return max(0.0, min(1.0, (0.45 * query_score) + (0.55 * quality_score) - duplicate_penalty))


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
                        "video_id": v.get("id"),
                    })
            # Evict oldest entries if cache is full
            if len(_pexels_cache) >= _PEXELS_CACHE_MAX:
                oldest = next(iter(_pexels_cache))
                del _pexels_cache[oldest]
            _pexels_cache[cache_key] = results
            return results

    return []


async def run_casting(job: EpisodeJob, broadcast_log) -> EpisodeJob:
    """Match each scene to a stock video clip using query expansion and quality ranking."""
    job.status = EpisodeStatus.CASTING
    await broadcast_log("CASTING", "info", "Starting scene-to-video matching...")

    if not job.blueprint:
        await broadcast_log("CASTING", "error", "No blueprint available")
        job.error_log.append("Casting: no blueprint")
        return job

    scene_assets: List[SceneAsset] = []
    used_video_urls: set[str] = set()
    if PEXELS_API_KEY:
        await broadcast_log("CASTING", "info", "Using smart keyword + quality ranking mode")

    for scene in job.blueprint.scenes:
        try:
            query = scene.visual_description
            search_queries = _build_search_queries(query, job.source_headline, scene.scene_number)

            # Primary: Pexels query expansion + clip quality ranking
            if PEXELS_API_KEY:
                best_video: dict | None = None
                best_score = -1.0
                best_query = ""

                for candidate_query in search_queries:
                    videos = await _search_pexels_videos(candidate_query, per_page=5)
                    for video in videos:
                        score = _ranked_video_score(
                            scene_query=query,
                            candidate_query=candidate_query,
                            headline=job.source_headline,
                            target_duration=scene.duration_seconds,
                            video=video,
                            already_used=video.get("url", "") in used_video_urls,
                        )
                        if score > best_score:
                            best_score = score
                            best_video = video
                            best_query = candidate_query

                if best_video and best_video.get("url"):
                    scene_assets.append(SceneAsset(
                        scene_number=scene.scene_number,
                        video_url=best_video["url"],
                        similarity_score=round(max(best_score, 0.0), 4),
                    ))
                    used_video_urls.add(best_video["url"])
                    await broadcast_log(
                        "CASTING", "success",
                        f"Scene {scene.scene_number}: matched via '{best_query}' (score: {best_score:.2f})"
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
    await broadcast_log("CASTING", "success", f"Casting complete. Avg match score: {avg_score:.2f}")
    return job
