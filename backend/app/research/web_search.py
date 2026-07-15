"""Pluggable web-search layer for the research engine.

Two integration modes are supported:

1. Anthropic native `web_search` server tool (default) — Claude runs the
   searches itself during a single Messages call. Nothing to do here beyond
   advertising the tool; see engine.py.

2. External providers (Tavily / Serper) — used when you want to feed search
   context into the model yourself, or when the native tool is unavailable.
   `search()` returns a list of {title, url, snippet} dicts.
"""
from __future__ import annotations

import logging

import httpx

from app.config import settings

log = logging.getLogger("research.web_search")


def anthropic_web_search_tool(max_uses: int = 6) -> dict:
    """Server-side web search tool definition for the Messages API."""
    return {"type": "web_search_20250305", "name": "web_search", "max_uses": max_uses}


def search(query: str, max_results: int = 6) -> list[dict]:
    provider = settings.web_search_provider
    try:
        if provider == "tavily" and settings.tavily_api_key:
            return _tavily(query, max_results)
        if provider == "serper" and settings.serper_api_key:
            return _serper(query, max_results)
    except Exception as exc:  # pragma: no cover - network dependent
        log.warning("web search failed for %r: %s", query, exc)
    return []


def _tavily(query: str, max_results: int) -> list[dict]:
    resp = httpx.post(
        "https://api.tavily.com/search",
        json={"api_key": settings.tavily_api_key, "query": query,
              "max_results": max_results, "search_depth": "advanced"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return [{"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("content", "")}
            for r in data.get("results", [])]


def _serper(query: str, max_results: int) -> list[dict]:
    resp = httpx.post(
        "https://google.serper.dev/search",
        headers={"X-API-KEY": settings.serper_api_key or "", "Content-Type": "application/json"},
        json={"q": query, "num": max_results},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    out = []
    for r in data.get("organic", [])[:max_results]:
        out.append({"title": r.get("title", ""), "url": r.get("link", ""), "snippet": r.get("snippet", "")})
    return out
