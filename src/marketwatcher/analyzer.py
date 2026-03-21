from __future__ import annotations

import logging
from typing import Optional

from openai import OpenAI

from .models import Listing, OpenAIConfig, WatchConfig

log = logging.getLogger("marketwatcher")


def analyze_listing(listing: Listing, watch: WatchConfig, config: OpenAIConfig) -> Optional[str]:
    """Ask ChatGPT whether the listing is below market price and worth buying.
    Returns a short verdict string, or None on failure."""
    if not config.enabled:
        return None

    price_display = listing.price_text or "Unknown"
    description = listing.description or "No description provided."
    location = listing.location_text or "Unknown location"

    prompt = (
        f"You are helping a buyer evaluate a second-hand listing on Facebook Marketplace.\n\n"
        f"Item being watched: {watch.name}\n"
        f"Listing title: {listing.title}\n"
        f"Price: {price_display} {watch.currency}\n"
        f"Location: {location}\n"
        f"Description: {description}\n\n"
        f"The buyer's maximum budget is {watch.max_price} {watch.currency}.\n\n"
        f"Is this listing priced below typical market value? Is it worth buying? "
        f"Reply in 2-3 concise sentences with a clear verdict."
    )

    try:
        client = OpenAI(
            api_key=config.api_key,
            organization=config.org_id,
        )
        response = client.chat.completions.create(
            model=config.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.4,
        )
        verdict = response.choices[0].message.content.strip()
        log.info("AI verdict for listing %s: %s", listing.stable_id, verdict)
        return verdict
    except Exception as exc:
        log.warning("OpenAI analysis failed for listing %s: %s", listing.stable_id, exc)
        return None
