"""Headless-browser crawler built on Playwright.

Fetches a page, extracts metadata and visible text, discovers outbound links,
and returns a structured result. All network activity happens in a real
Chromium instance so JS-heavy sites render properly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright

from . import config, filters


@dataclass
class PageData:
    url: str
    final_url: str
    title: str
    description: str
    body_text: str
    links: list[str] = field(default_factory=list)
    has_social_links: bool = False
    has_https: bool = True
    status: int = 200


_SOCIAL_RE = re.compile(
    r"(twitter\.com|x\.com|facebook\.com|linkedin\.com|instagram\.com|"
    r"youtube\.com|reddit\.com|t\.me|discord\.gg|bsky\.app|mastodon\.social)",
    re.IGNORECASE,
)


def _clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "")
    return text.strip()


async def _extract_links(page, base_url: str, limit: int) -> list[str]:
    """Collect outbound links, deduped, capped, and normalized."""
    try:
        hrefs = await page.eval_on_selector_all(
            "a[href]", "els => els.map(e => e.href).filter(Boolean)"
        )
    except Exception:
        return []

    seen: set[str] = set()
    out: list[str] = []
    for href in hrefs:
        try:
            full = urljoin(base_url, href)
            norm = filters.normalize_url(full)
        except Exception:
            continue
        if not norm:
            continue
        if norm in seen:
            continue
        seen.add(norm)
        out.append(norm)
        if len(out) >= limit:
            break
    return out


async def fetch_page(page, url: str) -> PageData:
    """Load a single URL in the given Playwright page and extract data."""
    resp = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    status = resp.status if resp else 0

    # Give JS a moment to render.
    try:
        await page.wait_for_timeout(1500)
    except Exception:
        pass

    title = ""
    try:
        title = _clean_text(await page.title())
    except Exception:
        pass

    description = ""
    try:
        desc = await page.eval_on_selector(
            'meta[name="description"]',
            "el => el.getAttribute('content') || ''",
        )
        description = _clean_text(desc)
    except Exception:
        pass

    body_text = ""
    try:
        body_text = _clean_text(
            await page.evaluate("document.body ? document.body.innerText : ''")
        )
    except Exception:
        pass

    links = await _extract_links(page, url, config.MAX_LINKS_PER_PAGE)

    has_social = bool(_SOCIAL_RE.search(f"{title} {body_text[:2000]}"))

    final_url = page.url or url
    has_https = final_url.startswith("https://")

    return PageData(
        url=url,
        final_url=final_url,
        title=title,
        description=description,
        body_text=body_text,
        links=links,
        has_social_links=has_social,
        has_https=has_https,
        status=status,
    )


async def crawl_urls(urls: list[str]) -> list[PageData]:
    """Crawl a list of URLs using a shared headless browser context."""
    results: list[PageData] = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0 Safari/537.36 SpiderCat/1.0"
            ),
            viewport={"width": 1280, "height": 800},
        )
        page = await context.new_page()
        for url in urls:
            try:
                data = await fetch_page(page, url)
                results.append(data)
            except Exception as exc:
                # Record a minimal failed result so the caller can log it.
                results.append(
                    PageData(
                        url=url,
                        final_url=url,
                        title="",
                        description="",
                        body_text="",
                        links=[],
                        status=0,
                    )
                )
                results[-1]._error = str(exc)  # type: ignore[attr-defined]
        await browser.close()
    return results
