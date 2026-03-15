"""News headline fetcher using NewsAPI and RSS fallback."""

from __future__ import annotations

import asyncio
import os
import random
from typing import List

import httpx
from dotenv import load_dotenv

load_dotenv()

NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")

# Fallback headlines for when NewsAPI is unavailable
FALLBACK_HEADLINES = [
    "Scientists Discover New Species of Deep-Sea Creature in Pacific Ocean",
    "Global Tech Summit Announces Breakthrough in Quantum Computing",
    "Space Agency Reveals Plans for First Human Settlement on Mars",
    "World Leaders Agree on Historic Climate Action Framework",
    "Artificial Intelligence System Passes Advanced Medical Licensing Exam",
    "Archaeologists Uncover Ancient City Beneath Modern Metropolis",
    "Revolutionary Battery Technology Could Double Electric Vehicle Range",
    "Ocean Cleanup Project Removes One Million Tons of Plastic",
    "New Telescope Captures First Direct Image of Exoplanet Atmosphere",
    "Breakthrough Gene Therapy Reverses Age-Related Vision Loss",
    "Autonomous Drone Fleet Completes First Transatlantic Cargo Delivery",
    "Underground Fungal Network Found to Communicate Across Entire Forest",
    "Fusion Reactor Achieves Net Energy Gain for First Time in History",
    "Deep Sea Mining Moratorium Proposed After New Ecosystem Discovery",
    "Robot Chef Wins International Cooking Competition Against Human Chefs",
]

_used_headlines: List[str] = []
_MAX_USED_HEADLINES = 100


async def fetch_headline() -> str:
    """Fetch a trending news headline. Falls back to curated list if API unavailable."""
    # Try NewsAPI first
    if NEWSAPI_KEY:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    "https://newsapi.org/v2/top-headlines",
                    params={"country": "us", "pageSize": 20, "apiKey": NEWSAPI_KEY},
                )
                if resp.status_code == 200:
                    articles = resp.json().get("articles", [])
                    titles = [
                        a["title"]
                        for a in articles
                        if a.get("title") and a["title"] not in _used_headlines
                    ]
                    if titles:
                        headline = titles[0]
                        _used_headlines.append(headline)
                        return headline
        except Exception:
            pass

    # Try RSS fallback (Google News)
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get("https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en")
            if resp.status_code == 200:
                import xml.etree.ElementTree as ET
                root = ET.fromstring(resp.text)
                items = root.findall(".//item/title")
                titles = [
                    item.text
                    for item in items
                    if item.text and item.text not in _used_headlines
                ]
                if titles:
                    headline = titles[0]
                    _used_headlines.append(headline)
                    return headline
    except Exception:
        pass

    # Final fallback: curated headlines
    available = [h for h in FALLBACK_HEADLINES if h not in _used_headlines]
    if not available:
        _used_headlines.clear()
        available = FALLBACK_HEADLINES[:]
    headline = random.choice(available)
    _used_headlines.append(headline)
    # Trim to cap memory usage
    if len(_used_headlines) > _MAX_USED_HEADLINES:
        _used_headlines[:] = _used_headlines[-_MAX_USED_HEADLINES:]
    return headline
