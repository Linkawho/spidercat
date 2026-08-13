"""Filtering rules.

Decides whether a discovered site is allowed to be auto-added. The spider only
auto-adds sites that are popular, well-known, and long-standing, and it never
auto-adds sites in blocked categories (NSFW, cloud gaming, search engines).
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

from . import config


def normalize_url(url: str) -> str:
    """Return a cleaned URL (lowercased host, no trailing slash, no fragment)."""
    url = url.strip()
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        p = urlparse(url)
    except ValueError:
        return ""
    host = (p.hostname or "").lower()
    if not host:
        return ""
    path = p.path.rstrip("/")
    return f"https://{host}{path}"


def extract_domain(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except ValueError:
        return ""


def _matches(text: str, keywords: list[str]) -> bool:
    """Match keywords using word boundaries to avoid false positives from
    substrings (e.g. 'sex' inside 'access', 'anal' inside 'analysis')."""
    text = text.lower()
    for kw in keywords:
        pattern = r"\b" + re.escape(kw) + r"\b"
        if re.search(pattern, text):
            return True
    return False


def is_nsfw(domain: str, title: str, description: str, body_text: str) -> bool:
    haystack = f"{domain} {title} {description} {body_text[:2000]}"
    return _matches(haystack, config.NSFW_KEYWORDS)


def is_cloud_gaming(domain: str, title: str, description: str, body_text: str) -> bool:
    haystack = f"{domain} {title} {description} {body_text[:2000]}"
    return _matches(haystack, config.CLOUD_GAMING_KEYWORDS)


def is_search_engine(domain: str, title: str, description: str, body_text: str) -> bool:
    haystack = f"{domain} {title} {description} {body_text[:2000]}"
    return _matches(haystack, config.SEARCH_ENGINE_KEYWORDS)


def is_dependency_registry(domain: str, title: str, description: str, body_text: str) -> bool:
    """True if the site is essentially a package/dependency registry or CDN.

    These are infrastructure, not interesting destinations, so they are never
    auto-added. The domain itself is checked too, since registries often have
    generic titles (e.g. 'npm').
    """
    haystack = f"{domain} {title} {description} {body_text[:2000]}"
    return _matches(haystack, config.DEPENDENCY_KEYWORDS)


def is_blocked_category(category: str) -> bool:
    return category in config.BLOCKED_AUTO_CATEGORIES


def is_known_well_known_domain(domain: str) -> bool:
    """Heuristic: a domain with a common TLD and no subdomain is more likely
    to be a well-known, long-standing site."""
    if not domain:
        return False
    # Reject obvious junk / placeholder domains.
    junk = re.search(
        r"(example\.com|example\.org|localhost|\.local$|\.test$|\.invalid$|"
        r"\.onion$|\.internal$|sentry\.|webhook\.|cdn\.|static\.|assets\.|"
        r"api\.|img\.|images\.|fonts\.|analytics\.|tracking\.)",
        domain,
    )
    if junk:
        return False
    # Reject IP addresses.
    if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", domain):
        return False
    return True


def popularity_score(
    title: str,
    description: str,
    body_text: str,
    *,
    has_social_links: bool = False,
    has_https: bool = True,
    domain_age_years: float | None = None,
) -> int:
    """A rough 0-10 popularity/authority score based on page signals.

    This is a stand-in for a real popularity API (e.g. Moz, Ahrefs, or a
    backlink index). When a real API is configured, it should override this.
    """
    score = 0
    text = f"{title} {description} {body_text[:4000]}".lower()

    # Presence of a real description / substantial content.
    if description and len(description) > 40:
        score += 2
    if len(body_text) > 500:
        score += 1
    if len(body_text) > 2000:
        score += 1

    # Social / sharing signals.
    if has_social_links:
        score += 1

    # HTTPS is a baseline expectation for modern well-known sites.
    if has_https:
        score += 1

    # Long-standing domain.
    if domain_age_years is not None:
        if domain_age_years >= 10:
            score += 2
        elif domain_age_years >= config.MIN_DOMAIN_AGE_YEARS:
            score += 1

    # Well-known brand keywords in the title.
    brand_hints = [
        "wikipedia", "youtube", "github", "google", "microsoft", "apple",
        "amazon", "facebook", "twitter", "reddit", "netflix", "spotify",
        "stack overflow", "mozilla", "adobe", "cloudflare", "python",
        "node.js", "linux", "ubuntu", "fedora", "weather", "news",
    ]
    for hint in brand_hints:
        if hint in text:
            score += 1
            break

    return min(score, 10)


def is_link_hub_without_novelty(
    links: list[str],
    known_domains: set[str],
) -> tuple[bool, str]:
    """True if a page is a "link hub" (many outbound links) whose links are
    mostly to already-known domains.

    A page that is mostly a directory of links to other well-known sites is not
    a good spider root: it would just re-crawl the same sites. We only treat a
    link-heavy page as a good root when a meaningful share of its outbound links
    point to brand-new domains we have not already seen.
    """
    if config.MIN_NOVEL_LINK_RATIO <= 0:
        return False, ""
    if len(links) < config.LINK_HUB_MIN_LINKS:
        return False, ""

    novel = 0
    for link in links:
        d = extract_domain(link)
        if d and d not in known_domains:
            novel += 1

    ratio = novel / len(links)
    if ratio < config.MIN_NOVEL_LINK_RATIO:
        return True, (
            f"link hub with only {novel}/{len(links)} novel links "
            f"(ratio {ratio:.0%} < {config.MIN_NOVEL_LINK_RATIO:.0%})"
        )
    return False, ""


def should_auto_add(
    *,
    domain: str,
    title: str,
    description: str,
    body_text: str,
    category: str,
    popularity: int,
    domain_age_years: float | None,
) -> tuple[bool, str]:
    """Return (allow, reason). Only well-known, popular, long-standing sites
    in non-blocked categories are auto-added."""
    if not is_known_well_known_domain(domain):
        return False, "domain looks like a CDN/placeholder/junk"

    if is_blocked_category(category):
        return False, f"category '{category}' is blocked from auto-adding"

    if is_nsfw(domain, title, description, body_text):
        return False, "NSFW content detected"

    if is_cloud_gaming(domain, title, description, body_text):
        return False, "cloud gaming content detected"

    if is_search_engine(domain, title, description, body_text):
        return False, "search engine / web index detected"

    if is_dependency_registry(domain, title, description, body_text):
        return False, "dependency/package registry or CDN detected"

    if popularity < config.MIN_POPULARITY_SCORE:
        return False, f"popularity score {popularity} below threshold"

    if domain_age_years is not None and domain_age_years < config.MIN_DOMAIN_AGE_YEARS:
        return False, f"domain age {domain_age_years:.1f}y below threshold"

    return True, "ok"
