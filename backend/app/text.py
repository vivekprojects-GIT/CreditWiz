"""The words of a query worth matching, shared by every search that matches text.

Mirrored in frontend/src/lib/hubSearch.ts, which matches pillar pages in the
browser. Keep the two word lists the same.
"""

from __future__ import annotations

import re

# Words that carry no subject: "how do I start a path for my role" is about
# paths and roles, and the rest would match every item in the catalog. "Agent"
# is on the list because on this hub nearly everything mentions one.
STOP_WORDS = frozenset(
    "a about against agent agents all also an and any are at be by can could do "
    "does for from get give has have how i in into is it just like me my need new "
    "of on or our out please should show some than that the their them then there "
    "they this to use using want was were what when where which who why will "
    "with would you your".split()
)
_SUFFIXES = ("ations", "ation", "ings", "ing", "ions", "ion", "ers", "er", "ed", "es", "ly", "al", "s", "e")


def stem(word: str) -> str:
    """One suffix off, never below four letters: "approved" and "approval"
    both become "approv", "screening" becomes "screen"."""
    for suffix in _SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            return word[: -len(suffix)]
    return word


def subject_stems(text: str) -> list[str]:
    """The words of a query worth matching, as stems."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    return list(dict.fromkeys(stem(w) for w in words if len(w) > 2 and w not in STOP_WORDS))


def word_starts(stems: list[str]) -> list[re.Pattern[str]]:
    """A stem counts only where a word starts: "check" and "list" are not a
    match for "checklist"."""
    return [re.compile(rf"\b{re.escape(s)}") for s in stems]
