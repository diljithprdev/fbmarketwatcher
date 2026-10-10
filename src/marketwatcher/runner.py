from __future__ import annotations

import logging

from .analyzer import analyze_listing
from .marketplace import MarketplaceBrowser
from .models import AppConfig
from .notifier import send_notification, send_no_new_listings
from .parser import matches_watch, parse_listings
from .state import SeenState

log = logging.getLogger("marketwatcher")


def run_scan_cycle(config: AppConfig, browser: MarketplaceBrowser, state: SeenState) -> None:
    """Execute one full scan cycle across all enabled watches."""
    enabled_watches = [w for w in config.watches if w.enabled]

    if not enabled_watches:
        log.warning("No enabled watches to scan.")
        return

    for watch in enabled_watches:
        log.info("Running watch: %s", watch.name)
        try:
            page = browser.open_url(watch.marketplace_url)
        except Exception as exc:
            log.error("[%s] Could not open URL: %s", watch.name, exc)
            continue

        try:
            listings = parse_listings(page, watch, config.scanner.max_listings_per_watch)
        except Exception as exc:
            log.error("[%s] Unexpected parse error: %s", watch.name, exc)
            listings = []
        finally:
            try:
                page.close()
            except Exception:
                pass

        notified_this_cycle: list[str] = []

        for listing in listings:
            sid = listing.stable_id

            if state.is_seen(sid):
                log.debug("[%s] Duplicate skipped: %s", watch.name, sid)
                continue

            if not matches_watch(listing, watch):
                continue

            price_display = listing.price_text or "N/A"
            log.info(
                "Match found: %s | %s %s",
                listing.title,
                price_display,
                watch.currency,
            )

            # Fetch full description from listing detail page
            listing.description = browser.fetch_description(listing.url)

            # Ask ChatGPT for a market value verdict
            if config.openai:
                listing.ai_verdict = analyze_listing(listing, watch, config.openai)

            sent = send_notification(listing, config.telegram)
            if sent:
                state.mark_seen(sid, watch.name)
                notified_this_cycle.append(sid)

        if notified_this_cycle:
            state.save()
            log.info("[%s] Notified %d new listings.", watch.name, len(notified_this_cycle))
        else:
            send_no_new_listings(watch.name, config.telegram)

    log.info("Scan cycle complete")
