from __future__ import annotations

import logging

import requests

from .models import Listing, TelegramConfig

log = logging.getLogger("marketwatcher")

_TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"
_TIMEOUT = 10  # seconds


def _format_message(listing: Listing) -> str:
    header = "MarketWatcher FREE match found" if listing.is_free else "MarketWatcher match found"
    price_display = listing.price_text or "Unknown"
    lines = [
        header,
        f"Watch: {listing.watch_name}",
        f"Title: {listing.title}",
        f"Price: {price_display}",
    ]
    if listing.location_text:
        lines.append(f"Location: {listing.location_text}")
    lines.append(f"URL: {listing.url}")
    if listing.ai_verdict:
        lines.append(f"\nAI Verdict: {listing.ai_verdict}")
    return "\n".join(lines)


def send_notification(listing: Listing, config: TelegramConfig) -> bool:
    """Send a Telegram message for *listing*. Returns True on success."""
    if not config.enabled:
        log.debug("Telegram disabled; skipping notification for %s", listing.stable_id)
        return False

    message = _format_message(listing)
    url = _TELEGRAM_API.format(token=config.bot_token)

    try:
        resp = requests.post(
            url,
            json={"chat_id": config.chat_id, "text": message},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        log.info("Notification sent for listing %s", listing.stable_id)
        return True
    except requests.RequestException as exc:
        log.error("Telegram send failed for listing %s: %s", listing.stable_id, exc)
        return False


def send_no_new_listings(watch_name: str, config: TelegramConfig) -> bool:
    """Send a 'no new listings' status message."""
    if not config.enabled:
        return False

    message = f"No new listings found for {watch_name}."
    url = _TELEGRAM_API.format(token=config.bot_token)

    try:
        resp = requests.post(
            url,
            json={"chat_id": config.chat_id, "text": message},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        log.info("No-new-listings message sent for %s", watch_name)
        return True
    except requests.RequestException as exc:
        log.error("Telegram send failed (no-new): %s", exc)
        return False
