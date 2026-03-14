"""Agent 1: Showrunner — Generates Production Blueprint from headline using Nova 2 Lite."""

from __future__ import annotations

import json
import os
import logging
import re

import boto3
from dotenv import load_dotenv

from models import Blueprint, EpisodeJob, EpisodeStatus

load_dotenv()
logger = logging.getLogger("novastream.showrunner")

NOVA_LITE_MODEL_ID = os.getenv("NOVA_LITE_MODEL_ID", "amazon.nova-2-lite-v1:0")
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
SHOWRUNNER_MAX_RETRIES = max(1, int(os.getenv("SHOWRUNNER_MAX_RETRIES", "1")))
SHOWRUNNER_MAX_TOKENS = max(200, int(os.getenv("SHOWRUNNER_MAX_TOKENS", "500")))
SHOWRUNNER_TEMPERATURE = float(os.getenv("SHOWRUNNER_TEMPERATURE", "0.4"))

SYSTEM_PROMPT = """You are a TV show producer. Given a news headline, create a Production Blueprint for a 60-second video episode.

Return ONLY a valid JSON object matching the schema below. No markdown, no preamble, no explanation. If you cannot comply, return the JSON with empty strings.

JSON Schema:
{
  "title": "string (max 80 chars, catchy episode title)",
  "tone": "dramatic | satirical | documentary",
  "scenes": [
    {
      "scene_number": 1,
      "visual_description": "string (max 120 chars, describes the visual for stock video search)",
      "voiceover_script": "string (max 60 words, narration for this scene)",
      "duration_seconds": 15
    }
  ]
}

Rules:
- Exactly 4 scenes, scene_number 1 through 4
- duration_seconds between 10 and 20
- voiceover_script max 60 words per scene
- visual_description should be vivid and specific for stock video matching
- Total episode should tell a complete narrative arc: setup, development, climax, resolution
"""


async def run_showrunner(job: EpisodeJob, broadcast_log) -> EpisodeJob:
    """Generate a production blueprint from the headline using Nova 2 Lite via Converse API."""
    job.status = EpisodeStatus.SCRIPTING
    await broadcast_log("SHOWRUNNER", "info", f"Generating blueprint for: {job.source_headline}")

    last_error = ""
    for attempt in range(SHOWRUNNER_MAX_RETRIES):
        try:
            user_prompt = f"Create a Production Blueprint for this headline:\n\n\"{job.source_headline}\""
            if last_error:
                user_prompt += f"\n\nPrevious attempt failed validation: {last_error}\nPlease fix and return valid JSON."

            client = boto3.client("bedrock-runtime", region_name=AWS_REGION)

            # Use the Converse API (correct API for Nova 2 Lite)
            response = client.converse(
                modelId=NOVA_LITE_MODEL_ID,
                messages=[{
                    "role": "user",
                    "content": [{"text": user_prompt}]
                }],
                system=[{"text": SYSTEM_PROMPT}],
                inferenceConfig={
                    "temperature": SHOWRUNNER_TEMPERATURE,
                    "maxTokens": SHOWRUNNER_MAX_TOKENS,
                },
            )

            # Parse Converse API response
            text = response["output"]["message"]["content"][0]["text"]

            # Strip markdown fences if present
            text = text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

            blueprint_data = json.loads(text)
            blueprint = Blueprint(**blueprint_data)
            job.blueprint = blueprint

            await broadcast_log("SHOWRUNNER", "success", f"Blueprint generated: \"{blueprint.title}\" ({blueprint.tone})")
            for scene in blueprint.scenes:
                await broadcast_log("SHOWRUNNER", "info", f"  Scene {scene.scene_number}: {scene.visual_description[:60]}...")

            return job

        except json.JSONDecodeError as e:
            last_error = f"Invalid JSON: {e}"
            await broadcast_log("SHOWRUNNER", "warn", f"Attempt {attempt+1}/{SHOWRUNNER_MAX_RETRIES} failed: {last_error}")
        except Exception as e:
            last_error = str(e)
            await broadcast_log("SHOWRUNNER", "warn", f"Attempt {attempt+1}/{SHOWRUNNER_MAX_RETRIES} failed: {last_error}")

    # All retries exhausted — use fallback blueprint
    await broadcast_log("SHOWRUNNER", "error", "All retries failed. Using fallback blueprint.")
    job.blueprint = _fallback_blueprint(job.source_headline)
    job.error_log.append(f"Showrunner failed after {SHOWRUNNER_MAX_RETRIES} attempts: {last_error}")
    return job


def _fallback_blueprint(headline: str) -> Blueprint:
    """Generate a simple fallback blueprint when Nova 2 Lite is unavailable."""
    stopwords = {
        "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with", "from", "at", "by",
        "is", "are", "was", "were", "be", "been", "as", "that", "this", "it", "its", "after",
        "amid", "over", "under", "into", "about", "new", "says", "say",
    }

    tokens = re.findall(r"[A-Za-z0-9']+", headline.lower())
    keywords = [t for t in tokens if len(t) > 3 and t not in stopwords]

    # Keep stable ordering while removing duplicates
    deduped = []
    for kw in keywords:
        if kw not in deduped:
            deduped.append(kw)

    kw1 = deduped[0] if len(deduped) > 0 else "breaking"
    kw2 = deduped[1] if len(deduped) > 1 else "news"
    kw3 = deduped[2] if len(deduped) > 2 else "global"
    kw4 = deduped[3] if len(deduped) > 3 else "update"

    return Blueprint(
        title=headline[:80],
        tone="documentary",
        scenes=[
            {
                "scene_number": 1,
                "visual_description": f"TV newsroom, anchor desk, screens showing {kw1} and {kw2} headline graphics",
                "voiceover_script": f"Breaking news today. {headline}. This story has captured global attention.",
                "duration_seconds": 15,
            },
            {
                "scene_number": 2,
                "visual_description": f"Street interviews and crowd reactions related to {kw1} and {kw3}",
                "voiceover_script": "Experts are weighing in from around the world, offering their analysis on what this means for the future.",
                "duration_seconds": 15,
            },
            {
                "scene_number": 3,
                "visual_description": f"Press conference podium, officials discussing {kw2}, {kw3}, and {kw4}",
                "voiceover_script": "Public reaction has been swift and divided, with many taking to social media to share their thoughts.",
                "duration_seconds": 15,
            },
            {
                "scene_number": 4,
                "visual_description": f"Global map animation, data overlays, and timelines tracking the {kw1} story",
                "voiceover_script": "As this story continues to develop, one thing is certain. The world is watching closely.",
                "duration_seconds": 15,
            },
        ],
    )
