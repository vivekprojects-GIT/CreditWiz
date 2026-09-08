"""Cached, validated learning catalogue.

The router used to call `_raw()` for every scoring pass, which re-read and
re-parsed learning.json each time: one /api/learning request parsed the 42 KB
file 24 times and re-ran pydantic validation on all of it. Parsing is now done
once and held behind a short TTL, mirroring marketplace.store.MarketplaceStore
so both pillars behave the same way.

Only the parsed catalogue is cached. Visibility depends on the signed-in user's
groups, so filtering stays per-request in the router.
"""

from __future__ import annotations

import copy
import json
import os
import threading
import time
from pathlib import Path

from .models import Item, LearningPath

def _data_dir() -> Path:
    """Resolved per read, not at import, so CREDITWIZ_DATA_DIR can be pointed
    somewhere else by a test or a deployment without reimporting the module."""
    return Path(
        os.environ.get(
            "CREDITWIZ_DATA_DIR", Path(__file__).resolve().parents[2] / "data"
        )
    )


# Short enough that editing the catalogue during a demo shows up without a
# restart, long enough that a burst of requests parses nothing.
_RELOAD_SECONDS = 5.0


class LearningStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._loaded_at = 0.0
        self._raw: dict = {}
        self._paths: list[LearningPath] = []
        self._items: list[Item] = []
        self._persona_paths: dict[str, list[str]] = {}

    def _refresh(self) -> None:
        now = time.monotonic()
        if self._items and now - self._loaded_at < _RELOAD_SECONDS:
            return
        with self._lock:
            # Re-check inside the lock: several threads can arrive together and
            # only one of them should pay for the parse.
            if self._items and now - self._loaded_at < _RELOAD_SECONDS:
                return
            from .router import validate_catalog

            raw = json.loads(
                (_data_dir() / "learning.json").read_text(encoding="utf-8")
            )
            paths, items = validate_catalog(raw)
            self._raw = raw
            self._paths = paths
            self._items = items
            self._persona_paths = {
                k: v
                for k, v in raw.get("persona_paths", {}).items()
                if not k.startswith("_")
            }
            self._loaded_at = now

    @property
    def raw(self) -> dict:
        """A copy. Handing out the cached dict would let one caller's edit
        corrupt the catalogue for every later request."""
        self._refresh()
        return copy.deepcopy(self._raw)

    @property
    def catalog(self) -> tuple[list[LearningPath], list[Item]]:
        self._refresh()
        return self._paths, self._items

    @property
    def persona_paths(self) -> dict[str, list[str]]:
        self._refresh()
        return self._persona_paths

    def invalidate(self) -> None:
        """Drop the cache. Tests that point CREDITWIZ_DATA_DIR somewhere new
        need the next read to come from the new location."""
        with self._lock:
            self._loaded_at = 0.0
            self._items = []


store = LearningStore()
