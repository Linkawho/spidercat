# SpiderCat

An **AI + headless-browser web spider** that discovers, auto-categorizes, and
indexes **popular, well-known, and long-standing** websites into a markdown
file, with progress auto-saved to a **SQLite** database.

## Features

- **Headless browsing** via Playwright (real Chromium) so JS-heavy sites render.
- **AI categorization** (OpenAI-compatible chat completions) with a keyword
  heuristic fallback when no API key is set.
- **AI root-URL discovery** — the LLM proposes new well-known root URLs to add
  as seeds as it crawls, so the spider grows its own root set over time.
  Proposals are validated against the safety filters before being accepted.
- **Safety filters** — the spider **never auto-adds** NSFW, cloud gaming, or
  search-engine/index sites. Those categories are only populated from the
  explicit seed list.
- **Popularity / longevity heuristics** — only sites that look well-known and
  long-standing are auto-added.
- **Auto-save** — every site, crawl attempt, and decision is written to SQLite
  immediately, so progress survives crashes.
- **Markdown index** regenerated after every batch.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

## Run

```bash
# Heuristic-only (no API key needed)
python -m spidercat.spider

# With AI categorization
export OPENAI_API_KEY=sk-...
python -m spidercat.spider

# Options
python -m spidercat.spider --max-pages 100 --no-ai --db spidercat.db --output index.md
```

## Configuration

Edit [`spidercat/config.py`](spidercat/config.py) to:

- Add **spider root URLs** to `SEED_URLS` (the crawler starts from these).
- Adjust categories, blocked categories, popularity thresholds, and crawl caps.
- Point the AI at a custom OpenAI-compatible endpoint via `OPENAI_BASE_URL`
  and `OPENAI_MODEL`.

## How it works

1. **Seed** — the configured root URLs are enqueued and stored as `seed` sites.
2. **Crawl** — pages are fetched in a headless browser; title, description,
   visible text, and outbound links are extracted.
3. **Categorize** — AI (or heuristic) assigns a category from the known list.
4. **Filter** — NSFW / cloud gaming / search-engine sites and low-popularity
   sites are rejected from auto-adding.
5. **Persist** — everything is written to SQLite immediately.
6. **Discover** — outbound links are enqueued (breadth-first, capped).
7. **Output** — `index.md` is regenerated after each batch.

## Database

The SQLite file (`spidercat.db` by default) holds:

- `sites` — every discovered site, its category, popularity, and status.
- `crawl_queue` — pending URLs for breadth-first crawling.
- `crawl_log` — an audit trail of every decision.
