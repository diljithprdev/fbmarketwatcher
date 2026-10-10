from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright

from .models import ScannerConfig

log = logging.getLogger("marketwatcher")

PROFILE_DIR = str(Path("data/chrome_profile").resolve())


class MarketplaceBrowser:
    """Manages a single Playwright browser instance across scan cycles."""

    def __init__(self, config: ScannerConfig) -> None:
        self._config = config
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        self._playwright = sync_playwright().start()
        self._context = self._playwright.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=self._config.headless,
        )
        log.info("Browser started (headless=%s, profile=%s)", self._config.headless, PROFILE_DIR)

    def _make_context(self) -> BrowserContext:
        storage_path = Path(self._config.storage_state_path)
        if storage_path.exists():
            log.debug("Restoring browser session from %s", storage_path)
            return self._browser.new_context(storage_state=str(storage_path))  # type: ignore[union-attr]
        log.debug("No saved session found; starting fresh browser context.")
        return self._browser.new_context()  # type: ignore[union-attr]

    def save_session(self) -> None:
        """Persistent context saves automatically — this is a no-op."""
        log.debug("Session auto-saved via persistent context.")

    def close(self) -> None:
        try:
            if self._context:
                self._context.close()
            if self._playwright:
                self._playwright.stop()
        except Exception as exc:  # noqa: BLE001
            log.warning("Error during browser shutdown: %s", exc)
        log.info("Browser closed.")

    # ------------------------------------------------------------------
    # Page helpers
    # ------------------------------------------------------------------

    def open_url(self, url: str) -> Page:
        """Open a URL in a new page and wait for it to settle."""
        if self._context is None:
            raise RuntimeError("Browser not started. Call start() first.")

        page = self._context.new_page()
        try:
            page.goto(url, timeout=self._config.page_load_timeout_ms, wait_until="domcontentloaded")
            page.wait_for_timeout(self._config.post_load_wait_ms)
        except Exception as exc:
            log.error("Page load failed for %s: %s", url, exc)
            page.close()
            raise
        return page

    def fetch_description(self, url: str) -> Optional[str]:
        """Open a listing detail page and return its description text."""
        try:
            page = self.open_url(url)
        except Exception as exc:
            log.warning("Could not load listing page for description: %s", exc)
            return None

        try:
            # Try common description containers; fall back to largest text block
            selectors = [
                "[data-testid='marketplace-pdp-description']",
                "div[class*='description']",
                "div[class*='Description']",
            ]
            for sel in selectors:
                el = page.query_selector(sel)
                if el:
                    text = (el.inner_text() or "").strip()
                    if text:
                        return text

            # Fallback: grab all visible paragraph-like text blocks and pick longest
            blocks = page.query_selector_all("div[role='main'] span")
            texts = [(b.inner_text() or "").strip() for b in blocks]
            texts = [t for t in texts if len(t) > 40]
            return max(texts, key=len) if texts else None
        except Exception as exc:
            log.warning("Failed to extract description from %s: %s", url, exc)
            return None
        finally:
            try:
                page.close()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    def __enter__(self) -> "MarketplaceBrowser":
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
