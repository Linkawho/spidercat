"""Markdown index generator.

Produces the README-style index with a table of contents and per-category
sections, matching the format shown in the task.
"""

from __future__ import annotations

from . import config


def _anchor(name: str) -> str:
    """GitHub-style anchor slug for a category heading."""
    slug = name.lower()
    slug = slug.replace("&", "and")
    slug = re_sub(r"[^a-z0-9 -]", "", slug)
    slug = slug.replace(" ", "-")
    return slug


def re_sub(pattern: str, repl: str, text: str) -> str:
    import re

    return re.sub(pattern, repl, text)


def _toc_line(name: str) -> str:
    return f"* [{name}](#{_anchor(name)})"


def _site_line(site) -> str:
    title = site["title"] or site["domain"]
    url = site["url"]
    desc = site["description"] or ""
    notes = site["notes"] or ""
    parts = [f"* [{title}]({url})"]
    if desc:
        parts.append(f" - {desc}")
    if notes:
        parts.append(f" (SIDENOTE: {notes})")
    return "".join(parts)


HEADER = """## Wait... <img width="25%" src="linkawho-logo.png"></img>

A curated directory that helps you discover the Internet.


***Find something worth clicking.***

## About this site

**Linkawho?** is inspired by *Jerry's Guide to the World Wide Web*, the hand-curated directory that later became Yahoo!. Like the original guide, **Linkawho?** aims to help people discover interesting and useful corners of the Internet through human curation rather than algorithms.
"""

FOOTER = r"""
---

*\[Copyright Sammy L. All rights reserved. DISCLAIMER: I AM NOT RESPONSIBLE FOR THE CONTENT OF ANY THIRD-PARTY WEBSITES LINKED FROM THIS SITE.\]*
"""


def generate_markdown(sites_by_category: dict[str, list]) -> str:
    lines: list[str] = []
    lines.append("## Index")
    lines.append("")
    for cat in config.CATEGORIES:
        if cat["name"] in sites_by_category and sites_by_category[cat["name"]]:
            lines.append(_toc_line(cat["name"]))
    lines.append("")

    for cat in config.CATEGORIES:
        sites = sites_by_category.get(cat["name"], [])
        if not sites:
            continue
        lines.append(f"## {cat['name']}")
        lines.append("")
        for site in sites:
            lines.append(_site_line(site))
        lines.append("")

    body = "\n".join(lines).rstrip() + "\n"
    return HEADER + body + FOOTER
