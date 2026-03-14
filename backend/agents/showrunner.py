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


def _headline_keywords(headline: str) -> list[str]:
    stopwords = {
        "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with", "from", "at", "by",
        "is", "are", "was", "were", "be", "been", "as", "that", "this", "it", "its", "after",
        "amid", "over", "under", "into", "about", "new", "says", "say", "will", "could", "their",
    }
    tokens = re.findall(r"[A-Za-z0-9']+", headline.lower())
    deduped: list[str] = []
    for token in tokens:
        if len(token) <= 3 or token in stopwords or token in deduped:
            continue
        deduped.append(token)
    return deduped


def _infer_topic(headline: str) -> str:
    text = headline.lower()
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


def _fallback_visuals(topic: str, keywords: list[str]) -> list[str]:
    kw1 = keywords[0] if len(keywords) > 0 else "breaking"
    kw2 = keywords[1] if len(keywords) > 1 else "news"
    kw3 = keywords[2] if len(keywords) > 2 else "global"

    topic_visuals = {
        "finance": [
            f"stock market trading screens showing {kw1} and {kw2} price movement",
            f"oil refinery, commodities charts, and energy market visuals for {kw1}",
            f"business district offices and traders reacting to {kw2}",
            f"global financial map, charts, and economic data tied to {kw3}",
        ],
        "space": [
            f"rocket launch pad and mission control screens about {kw1}",
            f"astronaut training, moon mission hardware, and {kw2} visuals",
            f"space agency press briefing and engineers discussing {kw3}",
            f"planetary map, spacecraft animation, and countdown graphics",
        ],
        "politics": [
            f"government building exterior and podium remarks about {kw1}",
            f"officials, flags, and media scrum focused on {kw2}",
            f"public reaction, protest crowd, and interview clips about {kw3}",
            f"world map, diplomacy visuals, and policy timeline graphics",
        ],
        "crime": [
            f"police vehicles, crime scene tape, and investigators linked to {kw1}",
            f"security footage style city street visuals related to {kw2}",
            f"law enforcement press conference and courthouse exterior for {kw3}",
            f"community gathering, candles, and ongoing investigation graphics",
        ],
        "health": [
            f"hospital corridor, medical staff, and patient care tied to {kw1}",
            f"laboratory research, microscope, and treatment visuals for {kw2}",
            f"doctor press briefing and healthcare workers discussing {kw3}",
            f"medical charts, public health map, and recovery timeline graphics",
        ],
        "climate": [
            f"extreme weather footage, storm clouds, and environmental impact of {kw1}",
            f"emergency crews, damaged streets, and disaster response for {kw2}",
            f"community cleanup, aerial aftermath, and rescue visuals about {kw3}",
            f"global climate map, forecast graphics, and data overlays",
        ],
        "technology": [
            f"technology lab, screens, and product visuals related to {kw1}",
            f"engineers, robotics, and close-up hardware shots tied to {kw2}",
            f"conference stage, keynote audience, and innovation footage for {kw3}",
            f"futuristic data visualization and digital network animation",
        ],
        "general": [
            f"headline graphics and newsroom visuals focused on {kw1} and {kw2}",
            f"public reaction and on-the-ground footage related to {kw1}",
            f"official statements and press conference visuals about {kw2} and {kw3}",
            f"global map animation and data timeline tracking the story",
        ],
    }
    return topic_visuals[topic]


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
    keywords = _headline_keywords(headline)
    visuals = _fallback_visuals(_infer_topic(headline), keywords)

    return Blueprint(
        title=headline[:80],
        tone="documentary",
        scenes=[
            {
                "scene_number": 1,
                "visual_description": visuals[0],
                "voiceover_script": f"Breaking news today. {headline}. This story has captured global attention.",
                "duration_seconds": 15,
            },
            {
                "scene_number": 2,
                "visual_description": visuals[1],
                "voiceover_script": "Experts are weighing in from around the world, offering their analysis on what this means for the future.",
                "duration_seconds": 15,
            },
            {
                "scene_number": 3,
                "visual_description": visuals[2],
                "voiceover_script": "Public reaction has been swift and divided, with many taking to social media to share their thoughts.",
                "duration_seconds": 15,
            },
            {
                "scene_number": 4,
                "visual_description": visuals[3],
                "voiceover_script": "As this story continues to develop, one thing is certain. The world is watching closely.",
                "duration_seconds": 15,
            },
        ],
    )
