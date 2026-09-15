"""Learning items for a request, best first.

Shared by the typeahead and the home assistant's learning pillar, so both
find the same items for the same words.
"""

from __future__ import annotations

from ..text import subject_stems, word_starts
from .models import Item


def score_items(needle: str, items: list[Item]) -> list[tuple[int, Item]]:
    """A title typed in part matches as it always has. A sentence matches an
    item carrying at least half of its subject words."""
    low = needle.strip().lower()
    stems = subject_stems(low)
    starts = word_starts(stems)
    needed = max(1, -(-len(stems) // 2))
    scored = []
    for i in items:
        text = " ".join([i.title, i.description, *i.topics, *i.tags]).lower()
        if low == "learning" or (low and low in text):
            score = len(stems) + 1
        else:
            score = sum(bool(p.search(text)) for p in starts)
            if not stems or score < needed:
                continue
        scored.append((score, i))
    scored.sort(key=lambda pair: -pair[0])
    return scored
