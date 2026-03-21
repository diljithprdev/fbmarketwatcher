from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Set

log = logging.getLogger("marketwatcher")


class SeenState:
    """Tracks listing identifiers that have already been notified."""

    def __init__(self, path: str) -> None:
        self._path = Path(path)
        self._seen: Set[str] = set()
        self._watch_map: Dict[str, str] = {}  # id -> watch_name

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Load state from disk. Creates an empty file if missing."""
        self._path.parent.mkdir(parents=True, exist_ok=True)

        if not self._path.exists():
            self._seen = set()
            self._watch_map = {}
            self._write()
            log.debug("State file not found; created empty state at %s", self._path)
            return

        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            self._seen = set(data.get("seen", []))
            self._watch_map = data.get("watch_map", {})
            log.debug("Loaded %d seen IDs from %s", len(self._seen), self._path)
        except (json.JSONDecodeError, OSError) as exc:
            log.warning("Could not load state file (%s); starting fresh.", exc)
            self._seen = set()
            self._watch_map = {}

    def save(self) -> None:
        """Persist current state to disk."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._write()
        log.debug("Saved %d seen IDs to %s", len(self._seen), self._path)

    def _write(self) -> None:
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps({"seen": sorted(self._seen), "watch_map": self._watch_map}, indent=2),
            encoding="utf-8",
        )
        tmp.replace(self._path)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def is_seen(self, identifier: str) -> bool:
        return identifier in self._seen

    def mark_seen(self, identifier: str, watch_name: str = "") -> None:
        self._seen.add(identifier)
        if watch_name:
            self._watch_map[identifier] = watch_name

    def clear_watch(self, watch_name: str) -> int:
        """Remove all seen IDs belonging to *watch_name*.
        Also removes untracked entries (saved before watch-name tracking was added).
        Returns count removed."""
        tracked = {sid for sid, name in self._watch_map.items() if name.lower() == watch_name.lower()}
        untracked = self._seen - set(self._watch_map.keys())
        to_remove = tracked | untracked
        self._seen -= to_remove
        for sid in tracked:
            del self._watch_map[sid]
        return len(to_remove)

    def list_watches(self) -> Dict[str, int]:
        """Return a count of seen IDs per watch name."""
        counts: Dict[str, int] = {}
        for name in self._watch_map.values():
            counts[name] = counts.get(name, 0) + 1
        return counts
