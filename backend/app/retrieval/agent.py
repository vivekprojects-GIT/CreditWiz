"""A pillar agent: query -> embedding -> hybrid -> relevance gate.

The pipeline Discover runs for agents (docs/search-flow.md), for any
catalogue. A pillar configures one with the collection it keeps, and hands
it the records the person may see.

    query       masked by the guardrails before any agent sees it
    embedding   MiniLM, the query as given
    hybrid      Chroma (meaning) and BM25 (exact words), each told what the
                person may see, ordered by closeness in meaning
    gate        kept if close in meaning (0.30, and 65% of the best) or a
                strong keyword hit (half the best keyword score, carrying
                half of the words typed)
    context     the caller reads each id's record from its source

Permission first and again after: the permitted set filters inside both
retrievers, and nothing outside it survives the gate.
"""

from __future__ import annotations

import hashlib
import threading
from dataclasses import dataclass, field
from time import perf_counter
from typing import Literal

from ..text import subject_stems, word_starts
from .index import Doc, KeywordIndex, SemanticIndex, Source

# Discover's floors (marketplace/search.py), measured for a bare query.
SIMILARITY_FLOOR = 0.30
RELATIVE_FLOOR = 0.65
KEYWORD_RELATIVE_FLOOR = 0.5
# A keyword rescue must rest on most of what was typed. One shared word, such
# as "best" in "best pizza near me", scores as high as a rare acronym and
# would rescue anything that happens to contain it. Half the query's terms:
# the rule every word search on Nexus already uses.
KEYWORD_COVERAGE = 0.5
# The shortlist each agent returns.
RESULT_LIMIT = 6

Retrieval = Literal["hybrid", "keyword"]


@dataclass(frozen=True)
class Candidate:
    id: str
    # What it is ordered by: its similarity, 0 when only its words matched.
    # Then the two signals themselves (either may be absent).
    score: float
    similarity: float | None
    keyword: float | None


@dataclass
class Found:
    candidates: list[Candidate]
    # "hybrid" when the vector index answered, "keyword" when it could not.
    retrieval: Retrieval
    embed_ms: int = 0
    # What each retriever proposed before the gate, best five, for the trace.
    proposed: dict[str, dict[str, float]] = field(default_factory=dict)


def semantic_order(similar: dict[str, float], keywords: dict[str, float]) -> list[str]:
    """Every retrieved id, closest in meaning first. A record only the keyword
    side found has no similarity, so it follows the ones that have, by its
    keyword score."""
    return sorted({*similar, *keywords}, key=lambda rid: (-similar.get(rid, 0.0), -keywords.get(rid, 0.0), rid))


def _closeness(c: Candidate) -> tuple[float, float]:
    return (c.similarity or 0.0, c.keyword or 0.0)


def gate(
    similar: dict[str, float],
    keywords: dict[str, float],
    permitted: frozenset[str],
    coverage: dict[str, float],
) -> list[Candidate]:
    """Keep only what is relevant from one query's two retrievals, closest in
    meaning first. A retriever always returns something; this decides what
    is shown. `coverage` is the share of the query's terms each keyword hit
    carries."""
    if not similar and not keywords:
        return []
    top_similarity = max(similar.values(), default=0.0)
    top_keyword = max(keywords.values(), default=0.0)

    def relevant(rid: str) -> bool:
        sim, kw = similar.get(rid, 0.0), keywords.get(rid, 0.0)
        close = sim >= SIMILARITY_FLOOR and sim >= top_similarity * RELATIVE_FLOOR
        strong_keyword = (
            kw > 0 and kw >= top_keyword * KEYWORD_RELATIVE_FLOOR and coverage.get(rid, 0.0) >= KEYWORD_COVERAGE
        )
        return close or strong_keyword

    return [
        Candidate(
            rid, round(similar.get(rid, 0.0), 4), round(similar[rid], 3) if rid in similar else None, keywords.get(rid)
        )
        for rid in semantic_order(similar, keywords)
        if rid in permitted and relevant(rid)
    ]


def _top(scores: dict[str, float]) -> dict[str, float]:
    return dict(sorted(scores.items(), key=lambda kv: -kv[1])[:5])


class RetrievalAgent:
    def __init__(self, name: str) -> None:
        # The collection it keeps.
        self.name = name
        self.semantic = SemanticIndex(name)
        self.keyword = KeywordIndex()
        self._lock = threading.Lock()
        self._marks: dict[str, str] = {}

    # ------------------------------------------------------------- ingestion

    def sync(self, source: Source, docs: list[Doc]) -> dict[str, int] | None:
        """Bring one source in line with its records. Cheap when nothing
        changed, one fingerprint over the texts, and None back."""
        mark = hashlib.sha256(
            "\n".join(f"{d.id}\t{d.owner}\t{d.text}" for d in sorted(docs, key=lambda d: d.id)).encode("utf-8")
        ).hexdigest()
        if self._marks.get(source) == mark:
            return None
        with self._lock:
            if self._marks.get(source) == mark:
                return None
            self.keyword.sync(source, docs)
            counts = self.semantic.sync(source, docs)
            self._marks[source] = mark
        return counts

    def add(self, doc: Doc) -> bool:
        """Ingest one record now: found by its words at once, and embedded and
        stored in the vector index. False when the vector index could not take
        it; it is still found by its words, and embedded at the next sync."""
        with self._lock:
            self.keyword.upsert(doc)
            self._marks.pop(doc.source, None)
            return self.semantic.upsert(doc)

    def remove(self, doc_id: str, source: Source) -> None:
        with self._lock:
            self.keyword.remove(doc_id)
            self.semantic.remove(doc_id)
            self._marks.pop(source, None)

    # ------------------------------------------------------------- retrieval

    def find(
        self,
        queries: list[str],
        allowed: set[str],
        *,
        prefer: set[str] | frozenset[str] = frozenset(),
        limit: int = RESULT_LIMIT,
    ) -> Found:
        """One request's candidates, best first.

        `queries` are the request's searches, as typed and as the planner
        rewrote it: each is retrieved and gated on its own and a record keeps
        its best showing, so a rewrite can add recall but never lose what the
        person's own words found. `prefer` is their own desk or role: it leads
        only at equal similarity, and never adds a record.
        """
        permitted = frozenset(allowed)
        semantic_up = self.semantic.available
        retrieval: Retrieval = "hybrid" if semantic_up else "keyword"
        kept: dict[str, Candidate] = {}
        proposed: dict[str, dict[str, float]] = {"semantic": {}, "keyword": {}}
        started = perf_counter()
        for q in dict.fromkeys(q.strip() for q in queries if q.strip()):
            similar = self.semantic.search(q, permitted) if semantic_up else {}
            keywords = self.keyword.search(q, permitted)
            for name, scores in (("semantic", similar), ("keyword", keywords)):
                for rid, s in scores.items():
                    proposed[name][rid] = max(s, proposed[name].get(rid, 0.0))
            passed = gate(similar, keywords, permitted, self.keyword.coverage(q, keywords))
            for c in passed:
                if c.id not in kept or _closeness(c) > _closeness(kept[c.id]):
                    kept[c.id] = c
        embed_ms = round((perf_counter() - started) * 1000)
        proposed = {name: _top(scores) for name, scores in proposed.items()}
        if not kept:
            return Found([], retrieval, embed_ms, proposed)

        shortlist = sorted(
            kept.values(), key=lambda c: (-(c.similarity or 0.0), c.id not in prefer, -(c.keyword or 0.0), c.id)
        )[:limit]

        return Found(shortlist, retrieval, embed_ms, proposed)


def _join(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def explain(c: Candidate, labels: list[str], queries: list[str]) -> str:
    """Why a record is here, from its own labels and the two signals: metadata
    anyone can check, not generated prose."""
    starts = word_starts(subject_stems(" ".join(queries)))
    # One label per spelling: a topic "Prompting" and a tag "prompting" are one.
    distinct = {label.lower(): label for label in reversed(labels) if label}
    matched = [label for low, label in reversed(distinct.items()) if any(s.search(low) for s in starts)]
    if matched:
        return f"Matches {_join(matched[:3])}."
    if c.similarity is not None and c.keyword is not None:
        return "Close in meaning to what you asked, and shares its words."
    if c.similarity is not None:
        return "Close in meaning to what you asked."
    return "Shares words with what you asked."
