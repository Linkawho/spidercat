"""Categorization: AI (OpenAI-compatible) with a heuristic fallback.

The AI categorizer is used when OPENAI_API_KEY is set. Otherwise a keyword
heuristic assigns a category. Either way, the result is validated against the
known category list and the blocked-category rules.
"""

from __future__ import annotations

import json
import re
from typing import Optional

import urllib.request

from . import config
from . import filters

# Keyword -> category mapping for the heuristic categorizer.
HEURISTIC_RULES: list[tuple[list[str], str]] = [
    (["search engine", "web index", "web directory", "search results", "duckduckgo",
      "startpage", "bing", "google search", "searx", "marginalia", "wiby"],
     "Search Engines and Web Indexes"),
    (["github", "git", "code editor", "ide", "package manager", "npm", "pypi",
      "programming", "developer", "api", "cloudflare", "tailscale", "vscode",
      "visual studio", "node.js", "python", "javascript", "coding", "software"],
     "Coding"),
    (["microsoft", "apple", "android", "google", "amazon", "meta", "big tech",
      "operating system", "phone os", "windows", "macos"],
     "Big Tech"),
    (["chatgpt", "gemini", "llm", "large language model", "ai assistant",
      "artificial intelligence", "chatbot", "gpt", "claude", "copilot"],
     "AI Large Language Models"),
    (["weather", "forecast", "temperature", "radar", "meteorolog", "climate"],
     "Weather"),
    (["linux distro", "linux distribution", "fedora", "ubuntu", "bazzite",
      "arch linux", "debian", "distro", "operating system for"],
     "Cool Linux Distros"),
    (["cloud gaming", "geforce now", "xbox cloud", "game pass", "streaming games",
      "play games", "cloud game"],
     "Cloud Gaming"),
    (["browser", "firefox", "chrome", "brave", "librewolf", "zen browser",
      "web browser", "privacy browser"],
     "Web browsers"),
    (["useless", "odd", "fun", "silly", "pointless", "weird", "joke", "typer",
      "pointer", "christmas", "cat bounce", "useless web"],
     "Delightfully Useless/Odd"),
    (["comic", "humor", "joke", "funny", "meme", "dad joke", "xkcd", "cartoon",
      "developer humor", "reaction"],
     "Comics & Humor"),
    (["satirical", "fake news", "satire", "parody", "onion", "hot tech takes"],
     "Satirical News"),
    (["personal site", "personal page", "blog", "about me", "portfolio",
      "my website", "homepage", "stallman", "donation"],
     "Personal pages"),
    (["video", "music", "streaming", "youtube", "multimedia", "watch", "listen"],
     "Multimedia"),
    (["photo", "graphic design", "video editing", "stock photo", "krita",
      "darktable", "kdenlive", "ardour", "audacity", "davinci", "design",
      "editing", "photoshop", "lightroom", "premiere", "daw"],
     "Graphic Design and Video Editing"),
    (["social network", "social media", "bluesky", "mastodon", "twitter",
      "facebook", "reddit", "follow", "community"],
     "Social Networks"),
    (["porn", "nsfw", "adult", "hentai", "rule34", "xxx"],
     "NSFW (Porn)"),
]


def _normalize_category(name: str) -> Optional[str]:
    """Map an arbitrary category string to one of the known categories."""
    if not name:
        return None
    name = name.strip()
    for cat in config.CATEGORY_NAMES:
        if name.lower() == cat.lower():
            return cat
    # Fuzzy: try to find a known category contained in the name.
    for cat in config.CATEGORY_NAMES:
        if cat.lower() in name.lower() or name.lower() in cat.lower():
            return cat
    return None


def heuristic_categorize(title: str, description: str, body_text: str) -> Optional[str]:
    text = f"{title} {description} {body_text[:3000]}".lower()
    for keywords, category in HEURISTIC_RULES:
        for kw in keywords:
            if kw in text:
                return category
    return None


def _ai_categorize(title: str, description: str, body_text: str) -> Optional[str]:
    """Call an OpenAI-compatible chat completions endpoint."""
    if not config.OPENAI_API_KEY:
        return None

    categories = ", ".join(config.CATEGORY_NAMES)
    prompt = (
        "You are a web directory categorizer. Given a website's title, "
        "description, and a snippet of its visible text, choose the single "
        "best category from this exact list:\n"
        f"{categories}\n\n"
        "Reply with ONLY the category name, nothing else.\n\n"
        f"Title: {title}\n"
        f"Description: {description}\n"
        f"Text snippet: {body_text[:1500]}"
    )

    payload = {
        "model": config.OPENAI_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": 20,
    }
    req = urllib.request.Request(
        f"{config.OPENAI_BASE_URL.rstrip('/')}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.OPENAI_API_KEY}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    content = data["choices"][0]["message"]["content"].strip()
    return _normalize_category(content)


def categorize(
    title: str,
    description: str,
    body_text: str,
    *,
    use_ai: bool = True,
) -> tuple[Optional[str], str]:
    """Return (category, source) where source is 'ai' or 'heuristic'."""
    if use_ai:
        cat = _ai_categorize(title, description, body_text)
        if cat:
            return cat, "ai"
    cat = heuristic_categorize(title, description, body_text)
    if cat:
        return cat, "heuristic"
    return None, "none"


def ai_propose_roots(
    title: str,
    description: str,
    body_text: str,
    *,
    max_roots: int = 3,
) -> list[dict]:
    """Ask the LLM to propose new well-known root URLs to add as seeds.

    Returns a list of {"url": ..., "category": ...} dicts. The LLM is
    instructed to only suggest popular, well-known, long-standing sites and
    to avoid NSFW, cloud gaming, and search-engine/index sites. Returns an
    empty list when no API key is configured or the response is unusable.
    """
    if not config.OPENAI_API_KEY:
        return []

    categories = ", ".join(config.CATEGORY_NAMES)
    prompt = (
        "You are a web directory curator. Based on the website described "
        "below, propose up to "
        f"{max_roots} additional well-known, popular, long-standing websites "
        "that belong in the same directory and would be good spider root URLs "
        "to crawl.\n\n"
        "RULES:\n"
        "- Only suggest famous, established sites (e.g. Wikipedia, Reddit, "
        "Stack Overflow, Mozilla, Adobe).\n"
        "- NEVER suggest NSFW/porn, cloud gaming, or search-engine/index "
        "sites.\n"
        "- Each suggestion must map to exactly one category from this list:\n"
        f"{categories}\n\n"
        "Reply with ONLY a JSON array, no markdown, no commentary. Format:\n"
        '[{"url": "https://example.com", "category": "Category Name"}]\n\n'
        f"Current site title: {title}\n"
        f"Current site description: {description}\n"
        f"Current site text snippet: {body_text[:1200]}"
    )

    payload = {
        "model": config.OPENAI_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.4,
        "max_tokens": 300,
    }
    req = urllib.request.Request(
        f"{config.OPENAI_BASE_URL.rstrip('/')}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.OPENAI_API_KEY}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        content = data["choices"][0]["message"]["content"].strip()
    except Exception:
        return []

    # Strip any markdown fences the model might add.
    content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content).strip()
    try:
        items = json.loads(content)
    except json.JSONDecodeError:
        # Try to extract the first JSON array via regex as a fallback.
        m = re.search(r"\[.*\]", content, re.DOTALL)
        if not m:
            return []
        try:
            items = json.loads(m.group(0))
        except json.JSONDecodeError:
            return []

    if not isinstance(items, list):
        return []

    proposals: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url", "")).strip()
        cat = _normalize_category(str(item.get("category", "")))
        if url and cat:
            proposals.append({"url": url, "category": cat})
    return proposals[:max_roots]
