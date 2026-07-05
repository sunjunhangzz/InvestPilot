"""Web search for Agent evidence round.

Tries Tavily first, falls back to SerpAPI.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()


def search_web(query: str, max_results: int = 3) -> list[dict[str, str]]:
    """Return [{title, url, snippet}] from web search.

    Tavily primary, SerpAPI fallback.
    """

    # Try Tavily first.
    tavily_key = os.getenv("TAVILY_API_KEY")
    if tavily_key:
        try:
            from tavily import TavilyClient  # type: ignore[import-untyped]
            client = TavilyClient(api_key=tavily_key)
            result = client.search(query, max_results=max_results)
            return [
                {"title": r["title"], "url": r["url"], "snippet": r.get("content", "")[:200]}
                for r in result.get("results", [])
            ]
        except Exception:
            pass

    # Fallback to SerpAPI.
    serp_key = os.getenv("SERPAPI_KEY")
    if serp_key:
        try:
            import requests
            resp = requests.get("https://serpapi.com/search", params={
                "q": query, "api_key": serp_key, "num": max_results,
            }, timeout=10)
            data = resp.json()
            return [
                {"title": r.get("title", ""), "url": r.get("link", ""), "snippet": r.get("snippet", "")[:200]}
                for r in data.get("organic_results", [])
            ]
        except Exception:
            pass

    return []
