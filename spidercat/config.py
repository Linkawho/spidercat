"""Configuration: categories, seed URLs, and filtering rules.

The spider only crawls "popular, well-known, and long-standing" sites. We
express that as a set of heuristics (see filters.py) plus an explicit blocklist
for categories that must never be auto-added (NSFW, cloud gaming, search
engines / web indexes).
"""

from __future__ import annotations

import os

# ---------------------------------------------------------------------------
# Categories (order matters: it drives the order of the generated index).
# Each category has a markdown anchor slug used in the table of contents.
# ---------------------------------------------------------------------------
CATEGORIES: list[dict] = [
    {"name": "Search Engines and Web Indexes", "slug": "Search-engines-and-Web-Indexes"},
    {"name": "Coding", "slug": "Coding"},
    {"name": "Big Tech", "slug": "Big-Tech"},
    {"name": "AI Large Language Models", "slug": "AI-Large-Language-Models"},
    {"name": "Weather", "slug": "Weather"},
    {"name": "Cool Linux Distros", "slug": "Cool-Linux-Distros"},
    {"name": "Cloud Gaming", "slug": "Cloud-Gaming"},
    {"name": "Web browsers", "slug": "Web-browsers"},
    {"name": "Delightfully Useless/Odd", "slug": "Delightfully-Useless-Odd"},
    {"name": "Comics & Humor", "slug": "Comics-Humor"},
    {"name": "Satirical News", "slug": "Satirical-News"},
    {"name": "Personal pages", "slug": "Personal-pages"},
    {"name": "Multimedia", "slug": "Multimedia"},
    {"name": "Graphic Design and Video Editing", "slug": "Graphic-Design-and-Video-Editing"},
    {"name": "Social Networks", "slug": "Social-Networks"},
    {"name": "NSFW (Porn)", "slug": "NSFW-Porn"},
]

CATEGORY_NAMES: list[str] = [c["name"] for c in CATEGORIES]

# ---------------------------------------------------------------------------
# Seed URLs. These are the "spider root URLs" the crawler starts from. They are
# all popular, well-known, long-standing sites. Add more as needed.
# ---------------------------------------------------------------------------
SEED_URLS: list[dict] = [
    # (url, expected_category)
    {"url": "https://www.startpage.com", "category": "Search Engines and Web Indexes"},
    {"url": "https://www.duckduckgo.com", "category": "Search Engines and Web Indexes"},
    {"url": "https://lite.duckduckgo.com", "category": "Search Engines and Web Indexes"},
    {"url": "https://noai.duckduckgo.com", "category": "Search Engines and Web Indexes"},
    {"url": "https://html.duckduckgo.com", "category": "Search Engines and Web Indexes"},
    {"url": "https://www.github.com", "category": "Coding"},
    {"url": "https://code.visualstudio.com/", "category": "Coding"},
    {"url": "https://www.vscode.dev", "category": "Coding"},
    {"url": "https://antigravity.google/", "category": "Coding"},
    {"url": "https://www.npmjs.com/", "category": "Coding"},
    {"url": "https://pypi.org/", "category": "Coding"},
    {"url": "https://nodejs.org/", "category": "Coding"},
    {"url": "https://www.python.org/", "category": "Coding"},
    {"url": "https://cloudflare.com", "category": "Coding"},
    {"url": "https://tailscale.com", "category": "Coding"},
    {"url": "https://microsoft.com", "category": "Big Tech"},
    {"url": "https://android.com", "category": "Big Tech"},
    {"url": "https://apple.com", "category": "Big Tech"},
    {"url": "https://chatgpt.com", "category": "AI Large Language Models"},
    {"url": "https://gemini.google.com", "category": "AI Large Language Models"},
    {"url": "https://weather.com", "category": "Weather"},
    {"url": "https://www.wunderground.com/", "category": "Weather"},
    {"url": "https://weather.gov", "category": "Weather"},
    {"url": "https://wttr.in", "category": "Weather"},
    {"url": "https://fedoraproject.org/", "category": "Cool Linux Distros"},
    {"url": "https://bazzite.gg/", "category": "Cool Linux Distros"},
    {"url": "https://ubuntu.com/download/server", "category": "Cool Linux Distros"},
    {"url": "https://xbox.com/play", "category": "Cloud Gaming"},
    {"url": "https://play.geforcenow.com", "category": "Cloud Gaming"},
    {"url": "https://librewolf.net", "category": "Web browsers"},
    {"url": "https://zen-browser.app/", "category": "Web browsers"},
    {"url": "https://brave.com/download", "category": "Web browsers"},
    {"url": "https://hackertyper.net/", "category": "Delightfully Useless/Odd"},
    {"url": "https://pointerpointer.com/", "category": "Delightfully Useless/Odd"},
    {"url": "https://isitchristmas.com/", "category": "Delightfully Useless/Odd"},
    {"url": "https://cat-bounce.com/", "category": "Delightfully Useless/Odd"},
    {"url": "https://icanhazdadjoke.com/", "category": "Comics & Humor"},
    {"url": "https://xkcd.com/", "category": "Comics & Humor"},
    {"url": "https://turnoff.us/", "category": "Comics & Humor"},
    {"url": "https://devhumor.com/", "category": "Comics & Humor"},
    {"url": "https://thecodinglove.com/", "category": "Comics & Humor"},
    {"url": "https://sparksammy.com", "category": "Satirical News"},
    {"url": "https://theonion.com/", "category": "Satirical News"},
    {"url": "https://nodemixaholic.com", "category": "Personal pages"},
    {"url": "https://coindrop.to/sam", "category": "Personal pages"},
    {"url": "https://patchmixolydic.com", "category": "Personal pages"},
    {"url": "https://stallman.org", "category": "Personal pages"},
    {"url": "https://youtube.com", "category": "Multimedia"},
    {"url": "https://music.youtube.com", "category": "Multimedia"},
    {"url": "https://unsplash.com/", "category": "Graphic Design and Video Editing"},
    {"url": "https://krita.org/", "category": "Graphic Design and Video Editing"},
    {"url": "https://darktable.org/", "category": "Graphic Design and Video Editing"},
    {"url": "https://kdenlive.org/", "category": "Graphic Design and Video Editing"},
    {"url": "https://ardour.org/", "category": "Graphic Design and Video Editing"},
    {"url": "https://www.audacityteam.org", "category": "Graphic Design and Video Editing"},
    {"url": "https://www.blackmagicdesign.com/products/davinciresolve", "category": "Graphic Design and Video Editing"},
    {"url": "https://bsky.app", "category": "Social Networks"},
    {"url": "https://pornhub.com", "category": "NSFW (Porn)"},
    {"url": "https://youporn.com", "category": "NSFW (Porn)"},
    {"url": "https://rule34.xxx", "category": "NSFW (Porn)"},
]

# ---------------------------------------------------------------------------
# Blocked categories: the spider must NEVER auto-add sites to these. They are
# only ever populated from the explicit seed list above.
# ---------------------------------------------------------------------------
BLOCKED_AUTO_CATEGORIES: set[str] = {
    "NSFW (Porn)",
    "Cloud Gaming",
    "Search Engines and Web Indexes",
}

# ---------------------------------------------------------------------------
# Keyword blocklists used by the heuristic filter. A site whose domain, title,
# description, or visible text matches these is rejected from auto-adding.
# ---------------------------------------------------------------------------
NSFW_KEYWORDS: list[str] = [
    "porn", "pornhub", "youporn", "xvideos", "xnxx", "rule34", "hentai",
    "nude", "naked", "sex", "erotic", "adult", "onlyfans", "camgirl",
    "escort", "milf", "boobs", "anal", "xxx", "nsfw", "fap", "redtube",
    "spankbang", "e621", "danbooru", "gelbooru", "nhentai", "porntrex",
]

CLOUD_GAMING_KEYWORDS: list[str] = [
    "cloud gaming", "cloudgaming", "geforce now", "xbox cloud", "xbox game pass",
    "stadia", "luna", "playstation now", "playstation plus", "boosteroid",
    "shadow pc", "airgpu", "blacknut", "antstream", "utomik", "vortex",
]

SEARCH_ENGINE_KEYWORDS: list[str] = [
    "search engine", "web index", "web directory", "search results",
    "google search", "bing", "duckduckgo", "startpage", "yahoo search",
    "brave search", "ecosia", "qwant", "mojeek", "searx", "marginalia",
    "wiby", "search.brave", "search engine and web index",
]

# Dependency / package registries and CDNs are infrastructure, not interesting
# destinations. A site that is essentially a package hub or content-delivery
# network is never auto-added.
DEPENDENCY_KEYWORDS: list[str] = [
    "package registry", "package manager", "package index", "dependency",
    "content delivery network", "cdn", "npm", "pypi", "maven", "crates.io",
    "rubygems", "nuget", "composer", "docker hub", "container registry",
    "apt", "homebrew", "chocolatey", "jsdelivr", "unpkg", "cdnjs",
    "esm.sh", "skypack", "registry.npmjs",
]

# ---------------------------------------------------------------------------
# Popularity / longevity heuristics.
# ---------------------------------------------------------------------------
# A site is considered "long-standing" if its domain has been registered for
# at least this many years (checked via WHOIS when available).
MIN_DOMAIN_AGE_YEARS: int = 3
# A site is considered "well-known" if it has at least this many backlinks
# reported by the (optional) popularity API. When no API is configured we fall
# back to a heuristic popularity score based on page signals.
MIN_POPULARITY_SCORE: int = 5
# Maximum number of outbound links to follow from a single page (breadth cap).
MAX_LINKS_PER_PAGE: int = 12
# Maximum total pages to crawl in one run.
MAX_PAGES_PER_RUN: int = 200

# ---------------------------------------------------------------------------
# Link-novelty heuristics. A page that is mostly a directory of links to other
# sites (a "link farm") is not a good spider root. We only auto-add a site when
# a meaningful share of its outbound links point to brand-new domains we have
# not already seen, so we don't keep re-crawling the same well-known sites.
# ---------------------------------------------------------------------------
# Minimum fraction of outbound links that must point to brand-new domains for a
# site to be considered a good root (0.0 = disabled).
MIN_NOVEL_LINK_RATIO: float = 0.5
# A site with at least this many outbound links is treated as a "link hub" and
# must meet the novelty ratio above; smaller pages are exempt from the check.
LINK_HUB_MIN_LINKS: int = 5

# ---------------------------------------------------------------------------
# AI configuration (OpenAI-compatible chat completions API).
# Leave OPENAI_API_KEY unset to use the heuristic categorizer instead.
# ---------------------------------------------------------------------------
OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY", "x")
OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "http://100.118.11.83:11434/v1")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "sparksammy/samantha-4-combo:small")

# ---------------------------------------------------------------------------
# Output / database paths.
# ---------------------------------------------------------------------------
DB_PATH: str = os.getenv("SPIDERCAT_DB", "spidercat.db")
OUTPUT_PATH: str = os.getenv("SPIDERCAT_OUTPUT", "../linkawho.github.io/LAW.md")
