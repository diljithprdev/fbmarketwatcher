from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from pydantic import BaseModel, field_validator


# ---------------------------------------------------------------------------
# Config models
# ---------------------------------------------------------------------------

class TelegramConfig(BaseModel):
    bot_token: str
    chat_id: str
    enabled: bool = True


class ScannerConfig(BaseModel):
    headless: bool = True
    scan_interval_seconds: int = 900
    page_load_timeout_ms: int = 45_000
    post_load_wait_ms: int = 3_000
    max_listings_per_watch: int = 50
    storage_state_path: str = "data/browser_state.json"


class StateConfig(BaseModel):
    seen_items_path: str = "data/seen_listings.json"


class WatchConfig(BaseModel):
    name: str
    enabled: bool = True
    marketplace_url: str
    max_price: float
    notify_on_free: bool = True
    currency: str = "GBP"
    keywords_include: List[str] = field(default_factory=list)
    keywords_exclude: List[str] = field(default_factory=list)

    @field_validator("keywords_include", "keywords_exclude", mode="before")
    @classmethod
    def _normalise_keywords(cls, v: object) -> List[str]:
        if v is None:
            return []
        return [kw.lower() for kw in v]  # type: ignore[union-attr]


class OpenAIConfig(BaseModel):
    api_key: str
    org_id: Optional[str] = None
    model: str = "gpt-4o-mini"
    enabled: bool = True


class AppConfig(BaseModel):
    telegram: TelegramConfig
    scanner: ScannerConfig = ScannerConfig()
    state: StateConfig = StateConfig()
    openai: Optional[OpenAIConfig] = None
    watches: List[WatchConfig] = []


# ---------------------------------------------------------------------------
# Listing data model
# ---------------------------------------------------------------------------

@dataclass
class Listing:
    watch_name: str
    listing_id: Optional[str]
    title: str
    price_text: Optional[str]
    price_value: Optional[float]
    is_free: bool
    url: str
    location_text: Optional[str]
    raw_text: str
    description: Optional[str] = None
    ai_verdict: Optional[str] = None

    @property
    def stable_id(self) -> str:
        """Prefer listing_id; fall back to normalised URL."""
        return self.listing_id or self.url
