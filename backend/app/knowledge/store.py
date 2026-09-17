"""The knowledge sources listing, read from data/knowledge-sources.json."""

from __future__ import annotations

import json
import os
from pathlib import Path

from .models import KnowledgeSources


def _data_dir() -> Path:
    return Path(os.environ.get("CREDITWIZ_DATA_DIR", Path(__file__).resolve().parents[2] / "data"))


def load() -> KnowledgeSources:
    """Read and validated on every call: the file is small, and an edit shows
    on the next request."""
    raw = json.loads((_data_dir() / "knowledge-sources.json").read_text(encoding="utf-8"))
    return KnowledgeSources.model_validate(raw)
