from __future__ import annotations

import logging
import re
from typing import List, Optional
from urllib.parse import urlparse

from playwright.sync_api import Page

from .models import Listing, WatchConfig

log = logging.getLogger("marketwatcher")

# Matches the numeric listing ID in a marketplace item URL
_LISTING_ID_RE = re.compile(r"/marketplace/item/(\d+)")

# Common price patterns: £280, $12.50, €9, or bare "280"
_PRICE_RE = re.compile(r"[\£\$\€]?\s*(\d[\d,]*(?:\.\d{1,2})?)")

FREE_TOKENS = frozenset(["free", "gratis", "£0", "$0", "€0"])


def _extract_listing_id(url: str) -> Optional[str]:
    m = _LISTING_ID_RE.search(url)
    return m.group(1) if m else None


def _normalise_url(url: str, base: str = "https://www.facebook.com") -> str:
    parsed = urlparse(url)
    if not parsed.scheme:
        return base + url
    return url


def _parse_price(text: str) -> tuple[Optional[float], bool]:
    """Return (numeric_price, is_free). Returns (None, True) for FREE items."""
    lower = text.lower().strip()
    if any(tok in lower for tok in FREE_TOKENS):
        return None, True
    m = _PRICE_RE.search(text)
    if m:
        try:
            value = float(m.group(1).replace(",", ""))
            return value, False
        except ValueError:
            pass
    return None, False


def _passes_keywords(text: str, watch: WatchConfig) -> bool:
    lower = text.lower()
    for kw in watch.keywords_include:
        if kw not in lower:
            return False
    for kw in watch.keywords_exclude:
        if kw in lower:
            return False
    return True


def parse_listings(page: Page, watch: WatchConfig, max_listings: int) -> List[Listing]:
    """
    Extract listing cards from a loaded Marketplace page.

    Strategy: find all anchor tags whose href contains /marketplace/item/,
    then read the surrounding card text. This is intentionally resilient to
    DOM layout changes.
    """
    listings: List[Listing] = []

    try:
        anchors = page.query_selector_all("a[href*='/marketplace/item/']")
    except Exception as exc:
        log.error("[%s] Failed to query listing anchors: %s", watch.name, exc)
        return listings

    seen_urls: set[str] = set()

    for anchor in anchors[:max_listings * 2]:  # over-fetch to account for nav links
        if len(listings) >= max_listings:
            break
        try:
            href = anchor.get_attribute("href") or ""
            if not href:
                continue
            url = _normalise_url(href)

            # De-duplicate within this page load
            if url in seen_urls:
                continue
            seen_urls.add(url)

            listing_id = _extract_listing_id(url)

            # Grab the visible text of the card (the anchor itself or its closest
            # meaningful parent — we try inner_text which includes child nodes).
            raw_text = (anchor.inner_text() or "").strip()

            if not raw_text:
                # Some anchors are icon-only; skip silently
                continue

            lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]
            title = lines[0] if lines else "Unknown"

            # Price is often the second line; search all lines for a price token
            price_text: Optional[str] = None
            price_value: Optional[float] = None
            is_free = False

            for line in lines:
                pv, free = _parse_price(line)
                if free:
                    is_free = True
                    price_text = "FREE"
                    break
                if pv is not None:
                    price_value = pv
                    price_text = line
                    break

            # Location is often the last meaningful line after the price
            location_text: Optional[str] = None
            if len(lines) >= 3:
                location_text = lines[-1]

            listing = Listing(
                watch_name=watch.name,
                listing_id=listing_id,
                title=title,
                price_text=price_text,
                price_value=price_value,
                is_free=is_free,
                url=url,
                location_text=location_text,
                raw_text=raw_text,
            )
            listings.append(listing)

        except Exception as exc:  # noqa: BLE001
            log.warning("[%s] Failed to parse a listing card: %s", watch.name, exc)
            continue

    log.info("Parsed %d listings for watch %s", len(listings), watch.name)
    return listings


def matches_watch(listing: Listing, watch: WatchConfig) -> bool:
    """Return True if the listing satisfies all watch rules."""
    if not _passes_keywords(listing.raw_text, watch):
        return False

    if listing.is_free and watch.notify_on_free:
        return True

    if listing.price_value is not None and listing.price_value <= watch.max_price:
        return True

    return False
