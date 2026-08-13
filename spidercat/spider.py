"""Main spider orchestration.

Flow:
1. Seed the crawl queue with the configured root URLs.
2. Crawl pages with the headless browser.
3. Categorize each page (AI or heuristic).
4. Filter out NSFW / cloud gaming / search engines / low-popularity sites.
5. Persist everything to SQLite immediately.
6. Discover outbound links and enqueue them (breadth-first, capped).
7. Regenerate the markdown index.
"""

from __future__ import annotations

import asyncio
import sys
from typing import Optional

from . import config, filters
from .categorizer import ai_propose_roots, categorize
from .crawler import crawl_urls
from .database import Database
from .markdown import generate_markdown


class Spider:
    def __init__(self, db: Database, *, use_ai: bool = True) -> None:
        self.db = db
        self.use_ai = use_ai

    # -- seeding -----------------------------------------------------------
    def seed(self) -> None:
        """Register the curated root URLs.

        Seed sites are always kept (they are hand-picked and well-known), so
        they are marked 'crawled' immediately so they appear in the index.

        Seeds in blocked categories (NSFW, cloud gaming, search engines) are
        listed but NEVER enqueued for crawling: we must not visit NSFW sites
        and must not use search engines / cloud gaming as spider roots.
        """
        for entry in config.SEED_URLS:
            url = filters.normalize_url(entry["url"])
            if not url:
                continue
            domain = filters.extract_domain(url)
            category = entry["category"]
            blocked = filters.is_blocked_category(category)
            self.db.upsert_site(
                url=url,
                domain=domain,
                category=category,
                category_source="seed",
                is_auto_added=0,
                status="crawled" if blocked else "pending",
            )
            if not blocked:
                self.db.enqueue(url, depth=0)
        self.db.log("", "seed", f"seeded {len(config.SEED_URLS)} root URLs")

    # -- processing --------------------------------------------------------
    def _known_domains(self) -> set[str]:
        """All domains we have already seen (seeds + discovered sites)."""
        return {filters.extract_domain(s["url"]) for s in self.db.all_sites()}

    def _process_page(self, data) -> None:
        """Categorize, filter, and persist a single crawled page."""
        url = filters.normalize_url(data.final_url or data.url)
        domain = filters.extract_domain(url)
        if not url or not domain:
            return

        # Skip pages whose title contains an HTTP error code (e.g. "404 Not
        # Found", "500 Internal Server Error"). These are dead/error pages.
        if filters.has_error_code_in_title(data.title):
            self.db.upsert_site(
                url=url, domain=domain, title=data.title,
                description=data.description, status="rejected",
                reject_reason="error code in title",
            )
            self.db.log(url, "rejected", "error code in title")
            return

        # If this URL is already a known seed, keep its seed category and
        # always keep it in the index (it is hand-picked and well-known).
        existing = self.db.get_site(url)
        if existing and existing["category_source"] == "seed":
            category = existing["category"]
            source = "seed"
            self.db.upsert_site(
                url=url, domain=domain, title=data.title,
                description=data.description, category=category,
                category_source="seed", is_auto_added=0, status="crawled",
            )
            self.db.log(url, "crawled", "seed site")
            return
        else:
            category, source = categorize(
                data.title, data.description, data.body_text, use_ai=self.use_ai
            )

        if not category:
            self.db.upsert_site(
                url=url, domain=domain, title=data.title,
                description=data.description, status="rejected",
                reject_reason="could not categorize",
            )
            self.db.log(url, "rejected", "could not categorize")
            return

        popularity = filters.popularity_score(
            data.title,
            data.description,
            data.body_text,
            has_social_links=data.has_social_links,
            has_https=data.has_https,
            domain_age_years=None,  # WHOIS lookup optional; see note below
        )

        allow, reason = filters.should_auto_add(
            domain=domain,
            title=data.title,
            description=data.description,
            body_text=data.body_text,
            category=category,
            popularity=popularity,
            domain_age_years=None,
        )

        # A page that is mostly a directory of links to already-known sites is
        # not a good spider root, so reject it even if it otherwise passes.
        if allow:
            hub, hub_reason = filters.is_link_hub_without_novelty(
                data.links, self._known_domains()
            )
            if hub:
                allow, reason = False, hub_reason

        if allow:
            self.db.upsert_site(
                url=url, domain=domain, title=data.title,
                description=data.description, category=category,
                category_source=source, popularity=popularity,
                is_auto_added=1, status="crawled",
            )
            self.db.log(url, "added", f"category={category} popularity={popularity}")
        else:
            self.db.upsert_site(
                url=url, domain=domain, title=data.title,
                description=data.description, category=category,
                category_source=source, popularity=popularity,
                is_auto_added=0, status="rejected", reject_reason=reason,
            )
            self.db.log(url, "rejected", reason)

    def _enqueue_links(self, data, depth: int) -> None:
        for link in data.links:
            self.db.enqueue(link, depth=depth + 1)

    def _add_proposed_roots(self, data) -> None:
        """Ask the LLM to propose new root URLs and add them as seeds.

        Proposed roots are validated: they must be in a non-blocked category,
        must not already be known, and must pass the NSFW/cloud-gaming/search
        filters. Accepted proposals are stored as seeds and enqueued.
        """
        if not self.use_ai:
            return
        proposals = ai_propose_roots(
            data.title, data.description, data.body_text, max_roots=3
        )
        for prop in proposals:
            url = filters.normalize_url(prop["url"])
            if not url:
                continue
            category = prop["category"]
            if filters.is_blocked_category(category):
                self.db.log(url, "root-skipped", f"blocked category {category}")
                continue
            if self.db.get_site(url):
                continue
            domain = filters.extract_domain(url)
            # Safety check on the proposed domain before trusting it.
            if filters.is_nsfw(domain, "", "", "") or \
               filters.is_cloud_gaming(domain, "", "", "") or \
               filters.is_search_engine(domain, "", "", ""):
                self.db.log(url, "root-skipped", "safety filter")
                continue
            self.db.upsert_site(
                url=url, domain=domain, category=category,
                category_source="ai-root", is_auto_added=0, status="pending",
            )
            self.db.enqueue(url, depth=0)
            self.db.log(url, "root-added", f"AI proposed {category}")
            print(f"  [ai-root] added {url} -> {category}", flush=True)

    # -- main loop ---------------------------------------------------------
    async def run(self, max_pages: int | None = None) -> None:
        max_pages = max_pages or config.MAX_PAGES_PER_RUN
        self.seed()

        processed = 0
        while processed < max_pages:
            batch: list[str] = []
            while len(batch) < 5:
                row = self.db.next_queued()
                if row is None:
                    break
                batch.append(row["url"])
            if not batch:
                break

            results = await crawl_urls(batch)
            for data in results:
                processed += 1
                self._process_page(data)
                self._enqueue_links(data, depth=0)
                self._add_proposed_roots(data)
                print(
                    f"[{processed}/{max_pages}] {data.final_url or data.url} "
                    f"-> {data.title[:60]!r}",
                    flush=True,
                )

            # Regenerate the index after each batch so progress is visible.
            self.write_index()

        self.db.log("", "done", f"processed {processed} pages")
        print(f"Done. Processed {processed} pages. Queue remaining: "
              f"{self.db.queue_size()}")

    # -- output ------------------------------------------------------------
    def write_index(self) -> None:
        sites = self.db.all_sites()
        by_cat: dict[str, list] = {}
        for site in sites:
            if site["status"] != "crawled":
                continue
            cat = site["category"] or "Uncategorized"
            by_cat.setdefault(cat, []).append(site)
        md = generate_markdown(by_cat)
        with open(config.OUTPUT_PATH, "w", encoding="utf-8") as fh:
            fh.write(md)


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="AI + headless-browser web spider")
    parser.add_argument("--max-pages", type=int, default=None,
                        help="max pages to crawl this run")
    parser.add_argument("--no-ai", action="store_true",
                        help="disable the AI categorizer (heuristic only)")
    parser.add_argument("--db", default=None, help="path to SQLite database")
    parser.add_argument("--output", default=None, help="path to markdown output")
    args = parser.parse_args(argv)

    if args.db:
        config.DB_PATH = args.db
    if args.output:
        config.OUTPUT_PATH = args.output

    db = Database(config.DB_PATH)
    try:
        spider = Spider(db, use_ai=not args.no_ai)
        asyncio.run(spider.run(max_pages=args.max_pages))
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
