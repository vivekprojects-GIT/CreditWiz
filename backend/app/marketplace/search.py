"""Generative / NLP search over agent metadata.

Two stages:

1. Understand intent.  If ANTHROPIC_API_KEY is configured, Claude turns the
   free-text request into a SearchIntent (summary, concepts, domains,
   capabilities, keywords).  Otherwise a local concept lexicon does the same job
   well enough for ten agents.
2. Match and rank.  Weighted field matching over the agent metadata, expanded
   with the intent's concepts and keywords, then boosted by persona relevance.

With ~10 agents this runs in microseconds and needs no vector store.  The
interface (SearchIntent -> ranked AgentMatch list) is the seam where a real
embedding index can be plugged in later.
"""

from __future__ import annotations

import logging
import os
import re

from . import keyword, semantic
from .models import Agent, AgentMatch, Persona, RerankedOrder, SearchIntent

log = logging.getLogger(__name__)

# ---------------------------------------------------------------- tokenising

_STOP = {
    "a", "an", "the", "i", "we", "me", "my", "our", "you", "your", "it", "is", "are", "be", "to", "of", "for", "in", "on",
    "at", "and", "or", "that", "this", "with", "can", "could", "would", "should", "need", "needs", "want", "wants",
    "looking", "look", "find", "something", "agent", "agents", "ai", "help", "helps", "please", "which", "what", "how",
    "do", "does", "any", "some", "there", "who", "will", "able", "tool", "tools", "one", "use",
}


def _stem(tok: str) -> str:
    for suf in ("isation", "ization", "ising", "izing", "ised", "ized", "ing", "ies", "ers", "er", "ed", "es", "s"):
        if tok.endswith(suf) and len(tok) - len(suf) >= 3:
            root = tok[: -len(suf)]
            return root + "y" if suf == "ies" else root
    return tok


def tokens(text: str) -> list[str]:
    return [_stem(t) for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in _STOP and len(t) > 1]


# ------------------------------------------------------- local intent lexicon
# trigger phrases -> (concept label, domains, capabilities, extra keywords)

_LEXICON: list[tuple[tuple[str, ...], str, list[str], list[str], list[str]]] = [
    (("onboard", "onboarding", "new customer", "application pack", "know your customer", "kyc"),
     "Customer onboarding / KYC", ["Onboarding", "Compliance"], ["Identity verification", "Completeness checking"],
     ["kyc", "identity", "onboarding", "application", "passport", "proof of address"]),
    (("identity", "passport", "driving licence", "proof of address", "id document", "verify"),
     "Identity verification", ["Onboarding", "Compliance"], ["Identity verification", "Document extraction"],
     ["kyc", "identity", "document"]),
    (("document", "documents", "paperwork", "pdf", "scan", "form", "extract", "read"),
     "Document review and extraction", [], ["Document extraction", "Completeness checking", "Summarisation"],
     ["document", "extract", "review", "ocr"]),
    (("contract", "agreement", "clause", "terms", "supplier", "vendor", "legal"),
     "Contract analysis", ["Legal"], ["Clause classification", "Playbook comparison", "Summarisation"],
     ["contract", "clause", "agreement", "legal"]),
    (("sanction", "sanctions", "pep", "aml", "screen", "screening", "money laundering",
      "watchlist", "watch list", "ofac", "due diligence"),
     "AML screening", ["Compliance", "Fraud & Risk"], ["Sanctions screening", "Risk scoring"],
     ["sanctions", "aml", "pep", "screening"]),
    (("fraud", "suspicious", "unusual", "investigat", "alert"),
     "Fraud investigation", ["Fraud & Risk"], ["Case summarisation", "Anomaly detection", "Investigation support"],
     ["fraud", "investigation", "alert", "case"]),
    (("dispute", "chargeback", "cardholder", "merchant", "reason code"),
     "Card disputes", ["Cards"], ["Case triage", "Rules checking"],
     ["dispute", "chargeback", "cards"]),
    (("collection", "collections", "arrears", "delinquent", "overdue", "debt", "recovery", "charged off", "charge-off", "payment plan"),
     "Collections and recovery", ["Collections"], ["Customer communication", "Asset discovery"],
     ["collections", "arrears", "recovery", "outreach"]),
    (("asset", "assets", "locate", "trace", "skip trace", "employer", "whereabouts"),
     "Asset and contact tracing", ["Collections"], ["Asset discovery", "Entity resolution"],
     ["asset", "locate", "recovery", "skip trace"]),
    (("policy", "policies", "regulation", "rule", "rules", "allowed", "compliant", "guidance", "procedure"),
     "Policy and regulatory guidance", ["Compliance"], ["Policy lookup", "Grounded Q&A", "Rules checking"],
     ["policy", "regulation", "guidance"]),
    (("email", "letter", "message", "sms", "write to", "reach out", "outreach", "communicat", "reply", "respond"),
     "Customer communication", ["Customer Service"], ["Customer communication", "Personalisation"],
     ["email", "outreach", "message", "customer"]),
    (("summar", "brief", "digest", "overview", "tl;dr"),
     "Summarisation", [], ["Summarisation", "Case summarisation"],
     ["summary", "brief"]),
    (("code", "pull request", "pr ", "github", "repo", "repository", "bug", "security", "review my", "developer", "test"),
     "Software engineering", ["Engineering"], ["Code review", "Security analysis", "Test generation"],
     ["code", "pull request", "github", "review", "developer"]),
    (("risk", "rating", "score", "scoring"),
     "Risk assessment", ["Fraud & Risk", "Compliance"], ["Risk scoring"],
     ["risk", "score"]),
    (("customer", "client", "applicant"),
     "Customer-facing work", ["Customer Service", "Onboarding"], [], ["customer"]),
]


def local_intent(query: str) -> SearchIntent:
    # Punctuation between words defeated substring triggers: the phrase
    # "money laundering" never matched "anti-money-laundering" because of the
    # hyphens. Flatten separators before looking for trigger phrases.
    q = " " + re.sub(r"[^a-z0-9]+", " ", query.lower()).strip() + " "
    concepts: list[str] = []
    domains: list[str] = []
    caps: list[str] = []
    keywords: list[str] = []
    for triggers, label, doms, cps, kws in _LEXICON:
        if any(t in q for t in triggers):
            concepts.append(label)
            for d in doms:
                if d not in domains:
                    domains.append(d)
            for c in cps:
                if c not in caps:
                    caps.append(c)
            for k in kws:
                if k not in keywords:
                    keywords.append(k)
    summary = "Looking for " + (", ".join(concepts[:3]).lower() if concepts else "an agent matching your description")
    return SearchIntent(summary=summary, concepts=concepts, domains=domains, capabilities=caps, keywords=keywords)


# ---------------------------------------------------------- optional Claude

# Sonnet 5 interprets a search request in ~3s; Opus 5 is more thorough but takes ~30s,
# too slow for a search box. Override with CREDITWIZ_SEARCH_MODEL.
_DEFAULT_MODEL = "claude-sonnet-5"


def _model() -> str:
    return os.environ.get("CREDITWIZ_SEARCH_MODEL", _DEFAULT_MODEL)


def claude_available() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY")) and os.environ.get("CREDITWIZ_DISABLE_LLM") not in ("1", "true")


def claude_intent(query: str, agents: list[Agent]) -> SearchIntent | None:
    """Ask Claude to interpret the request. Returns None on any failure so the caller falls back."""
    try:
        import anthropic
    except ImportError:
        return None
    domains = sorted({d for a in agents for d in a.business_domains})
    caps = sorted({c for a in agents for c in a.capabilities})
    system = (
        "You interpret an employee's plain-language request for an internal AI agent marketplace at a credit company. "
        "Return a short summary of what they need (one sentence, start with 'Looking for'), the underlying concepts, "
        "and pick only from the provided domain and capability lists. Add up to 8 extra keywords that would appear in "
        "the metadata of a matching agent.\n"
        f"Domains: {', '.join(domains)}\nCapabilities: {', '.join(caps)}"
    )
    try:
        model = _model()
        client = anthropic.Anthropic(timeout=20.0, max_retries=1)
        kwargs: dict = {}
        if "haiku" not in model:  # Haiku 4.5 rejects the effort parameter
            kwargs["output_config"] = {"effort": "low"}
        response = client.messages.parse(
            model=model,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": query}],
            output_format=SearchIntent,
            **kwargs,
        )
        if response.stop_reason == "refusal" or response.parsed_output is None:
            return None
        intent = response.parsed_output
        intent.domains = [d for d in intent.domains if d in domains]
        intent.capabilities = [c for c in intent.capabilities if c in caps]
        return intent
    except Exception as exc:  # noqa: BLE001 - any API failure degrades to local search
        log.warning("Claude intent failed, using local search: %s", exc)
        return None


_INTENT_CACHE: dict[str, SearchIntent] = {}
_INTENT_CACHE_MAX = 256


def understand(query: str, agents: list[Agent]) -> tuple[SearchIntent, str]:
    if claude_available():
        key = f"{_model()}|{query.strip().lower()}"
        cached = _INTENT_CACHE.get(key)
        if cached is not None:
            return cached, "claude"
        intent = claude_intent(query, agents)
        if intent is not None:
            if len(_INTENT_CACHE) >= _INTENT_CACHE_MAX:
                _INTENT_CACHE.pop(next(iter(_INTENT_CACHE)))
            _INTENT_CACHE[key] = intent
            return intent, "claude"
    return local_intent(query), "local"


# -------------------------------------------------------------- matching
#
# Typed search is hybrid retrieval over the agent metadata. The request --
# enriched with what we understood from it -- is embedded once and compared
# with every agent's embedded description, and scored separately by BM25 over
# the same text. The two rankings are fused by rank, not by score.
#
# Deliberately absent: per-field lexical weights, popularity and persona
# multipliers. Each grew for a reason, and together they were three tuning
# knobs explaining one ordering. Fusion is the one exception, and it earns its
# place by needing no weight at all: RRF reads ranks, so there is nothing to
# tune between the two retrievers. The
# Recommended-for-you carousel keeps its arithmetic (curation, below) because
# that per-component table is a review asset; a typed query does not need it.

# Cosine has no notion of "nothing else is relevant" -- it always fills top-K,
# so without a floor a sanctions query lists the Asset Locator. Two floors: an
# absolute one, and a relative one against the best hit, because a strong top
# result makes a 0.47 look like noise where a weak one would not.
#
# Measured on this catalogue with the EXPANDED query: real matches 0.54-0.85,
# noise 0.35-0.47. The number depends on the shape of what is embedded as much
# as on the model -- searching the bare query instead needs roughly 0.30, since
# a short question scores far lower for the same meaning. Retune if either the
# model or the expansion changes.
SIMILARITY_FLOOR = 0.45
RELATIVE_FLOOR = 0.65
# Rank fusion constant. 60 is the value from the original RRF paper and the one
# nearly every hybrid-search implementation uses; it damps the gap between rank
# 1 and rank 2 so one ranker's top hit cannot dominate on its own.
RRF_K = 60
# A keyword hit counts as strong at half the best keyword score. Exact names and
# acronyms score far above incidental term overlap, so this keeps the former and
# drops the latter.
KEYWORD_RELATIVE_FLOOR = 0.5

# How many matches a search returns. Fixed, not a caller-supplied knob: the
# gate above decides what is relevant, and a caller asking for twenty results
# would only be served the ones the gate already let through.
RESULT_LIMIT = 6


def retrieval_text(query: str, intent: SearchIntent) -> str:
    """The text that gets embedded: the query plus what we understood from it.

    Bare words embed weakly -- "code" alone lands at 0.26 against the Code
    Review Assistant, "is my code safe to merge" at 0.088 -- because a short
    question shares little surface with a catalogue entry. Folding in the
    restatement, domains and capabilities is query expansion done once, before
    the single retrieval. Understanding informs the search; it does not rank it.
    """
    parts = [
        query.strip(),
        intent.summary,
        ", ".join(intent.domains),
        ", ".join(intent.capabilities),
    ]
    return ". ".join(part for part in parts if part)


def keyword_text(query: str, intent: SearchIntent) -> str:
    """What the keyword ranker sees: the typed words plus the extracted domains
    and capabilities. Not the restatement -- prose dilutes exact tokens, which
    are the whole reason a keyword ranker is here."""
    parts = (query.strip(), ", ".join(intent.domains), ", ".join(intent.capabilities))
    return ". ".join(p for p in parts if p)


def rrf(*rankings: dict[str, float], k: int = RRF_K) -> dict[str, float]:
    """Reciprocal Rank Fusion: score = sum over rankers of 1 / (k + rank).

    Rank-based, so a cosine similarity in 0..1 and a BM25 score in 0..10 fuse
    without either scale dominating. An earlier hybrid blended the raw scores
    and let lexical noise outvote a correct semantic top hit; this cannot.
    """
    fused: dict[str, float] = {}
    for ranking in rankings:
        for rank_index, agent_id in enumerate(
            sorted(ranking, key=lambda i: -ranking[i])
        ):
            fused[agent_id] = fused.get(agent_id, 0.0) + 1.0 / (k + rank_index + 1)
    return fused


def rank(
    query: str,
    intent: SearchIntent,
    agents: list[Agent],
    persona: Persona | None = None,
    domain: str | None = None,
    limit: int = RESULT_LIMIT,
    similar: dict[str, float] | None = None,
    keywords: dict[str, float] | None = None,
) -> list[AgentMatch]:
    """Hybrid search: semantic and keyword candidates fused by rank.

    `similar` / `keywords` let the router pass retrievals it already ran, so the
    query is embedded once for both the ranking and the trace.

    RRF orders the union, but it has no notion of "nothing is relevant" -- it
    always returns whatever either ranker returned. A relevance gate keeps a
    candidate only if it is close semantically (both floors) OR is a strong
    keyword hit. "zebra origami" clears neither and returns no match.
    """
    if similar is None and semantic.index.available:
        similar = semantic.index.search(retrieval_text(query, intent))
    similar = similar or {}
    if keywords is None:
        if keyword.index.size == 0:
            from .store import store as agent_store

            keyword.index.sync(agent_store.all_agents)
        keywords = keyword.index.search(keyword_text(query, intent))
    if not similar and not keywords:
        return []

    top_similarity = max(similar.values(), default=0.0)
    top_keyword = max(keywords.values(), default=0.0)

    def relevant(agent_id: str) -> bool:
        sim = similar.get(agent_id, 0.0)
        kw = keywords.get(agent_id, 0.0)
        close = sim >= SIMILARITY_FLOOR and sim >= top_similarity * RELATIVE_FLOOR
        strong_keyword = kw > 0 and kw >= top_keyword * KEYWORD_RELATIVE_FLOOR
        return close or strong_keyword

    # `agents` is already the caller's visible subset. Both indexes cover the
    # whole catalogue, so an agent this user may not see can be retrieved; it is
    # dropped here by construction and can never surface.
    by_id = {agent.id: agent for agent in agents}
    fused = rrf(similar, keywords)
    matches: list[AgentMatch] = []
    for agent_id, score in sorted(fused.items(), key=lambda kv: -kv[1]):
        agent = by_id.get(agent_id)
        if agent is None or not relevant(agent_id):
            continue
        if domain and domain not in agent.business_domains:
            continue
        matches.append(
            AgentMatch(
                agent=agent,
                score=round(score, 4),
                similarity=round(similar[agent_id], 3) if agent_id in similar else None,
                keyword=keywords.get(agent_id),
                why=_why(agent, intent, persona),
                reasons=_reasons(agent, intent, persona),
                coverage=_coverage(agent, intent),
            )
        )
    return matches[:limit]


RERANK_CANDIDATES = 10


def rerank(query: str, matches: list[AgentMatch]) -> tuple[list[AgentMatch], str]:
    """Reorder fused candidates by reading them against the request.

    RRF orders by agreement between two retrievers, which is a proxy for
    relevance rather than a judgement about it: neither retriever ever compares
    a candidate with the request as a whole. This does, over the shortlist only,
    where the cost is bounded.

    Returns the matches and how they were ordered, so the trace can say which.
    Any failure returns the fused order untouched -- a reranker that cannot run
    must never cost a user their results.
    """
    if len(matches) < 2 or not claude_available():
        return matches, "fusion"
    shortlist = matches[:RERANK_CANDIDATES]
    catalogue = "\n".join(
        f"{m.agent.id}: {m.agent.name}. {m.agent.tagline} "
        f"Capabilities: {', '.join(m.agent.capabilities)}."
        for m in shortlist
    )
    system = (
        "You rank internal AI agents against an employee's request. Return the ids "
        "in order, best first, using only ids from the list. Drop an agent only if "
        "it is clearly irrelevant to the request. Judge fit to the request, not how "
        "impressive the agent sounds."
    )
    try:
        import anthropic

        client = anthropic.Anthropic(timeout=20.0, max_retries=1)
        model = _model()
        kwargs: dict = {}
        if "haiku" not in model:
            kwargs["output_config"] = {"effort": "low"}
        response = client.messages.parse(
            model=model,
            max_tokens=512,
            system=system,
            messages=[
                {
                    "role": "user",
                    "content": f"Request: {query}\n\nAgents:\n{catalogue}",
                }
            ],
            output_format=RerankedOrder,
            **kwargs,
        )
        if response.stop_reason == "refusal" or response.parsed_output is None:
            return matches, "fusion"
        by_id = {m.agent.id: m for m in shortlist}
        ordered = [by_id[i] for i in response.parsed_output.order if i in by_id]
        if not ordered:
            return matches, "fusion"
        # Anything the reranker did not mention keeps its fused position behind
        # what it did rank, so a truncated reply cannot silently lose results.
        named = {m.agent.id for m in ordered}
        rest = [m for m in matches if m.agent.id not in named]
        return ordered + rest, "claude"
    except Exception as exc:  # noqa: BLE001 - a failed rerank keeps the fused order
        log.warning("Rerank failed, keeping fused order: %s", exc)
        return matches, "fusion"


def _coverage(agent: Agent, intent: SearchIntent) -> int | None:
    """What share of the understood request this agent actually covers.

    A defensible percentage needs a definition the reader can check. This one
    is: of the domains and capabilities we extracted from the query, how many
    does this agent have? Nothing extracted means no percentage rather than a
    made-up one.
    """
    wanted = [*intent.domains, *intent.capabilities]
    if not wanted:
        return None
    have = [*agent.business_domains, *agent.capabilities]
    return round(100 * _covered(have, wanted) / len(wanted))


def _join(items: list[str]) -> str:
    items = [i for i in items if i]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]


def _matched(agent: Agent, intent: SearchIntent) -> tuple[list[str], list[str]]:
    """The agent's own capabilities and domains that the understood request
    asked for. Metadata, not generated prose -- the explanation is checkable."""
    caps = [c for c in agent.capabilities if _covered([c], intent.capabilities)]
    doms = [d for d in agent.business_domains if _covered([d], intent.domains)]
    return caps, doms


def _why(agent: Agent, intent: SearchIntent, persona: Persona | None) -> str:
    caps, doms = _matched(agent, intent)
    parts: list[str] = []
    if caps:
        parts.append("covers " + _join([c.lower() for c in caps[:3]]))
    if doms:
        parts.append("works in " + _join(doms[:2]))
    sentence = (
        f"This agent {', '.join(parts)}."
        if parts
        else "This agent is the closest match to how you described the need."
    )
    if persona and persona.id in agent.personas:
        sentence += f" It is built for {persona.label.lower()}s."
    return sentence


def _reasons(agent: Agent, intent: SearchIntent, persona: Persona | None) -> list[str]:
    caps, doms = _matched(agent, intent)
    reasons: list[str] = []
    if caps:
        reasons.append("Capabilities: " + ", ".join(caps[:3]))
    if doms:
        reasons.append("Domain: " + ", ".join(doms[:2]))
    if persona and persona.id in agent.personas:
        reasons.append(f"Built for {persona.label.lower()}s")
    if not reasons:
        reasons.append("Closest semantic match to your request")
    return reasons[:4]


# --- curation ---------------------------------------------------------------
# MVP implementation design (ours, not a client requirement): a transparent,
# explainable curation score. Deliberately rule-based, not a learned model, so
# every position in "Recommended for you" can be justified in review.
#
#   domain +3 each | capability +2 each | use case +2 each (capped) | tag +1 each
#   persona named by the owner: +25% of the above | popularity = tie-breaker
#
# Relevance is derived from business metadata. An agent that never names a
# persona still ranks on its domains, capabilities and tags, which is what lets
# this scale past a catalogue somebody hand-curated.
#
# Inputs are the derived persona and static agent metadata ONLY. Behavioural
# footprints (app/context) are collected but deliberately not read here.

CURATION_WEIGHTS = {"domain": 3.0, "capability": 2.0, "use_case": 2.0, "tag": 1.0}
# Use cases are sentences, and a wordy agent can list several. Without a cap a
# verbose listing would outrank a precise one on prose volume alone.
USE_CASE_CAP = 3
# An owner writing "designed for compliance users" is a curator hint, not
# evidence in itself. It scales what the business metadata already shows rather
# than adding a flat score, so a stray persona tag on an unrelated agent lifts
# nothing: 25% of zero is zero. The previous flat +10 outvoted every real
# signal -- an agent with one domain match and a persona tag beat an agent with
# three domain, three capability and three tag matches without one.
PERSONA_BOOST = 0.25


def _covered(agent_values: list[str], wanted: list[str]) -> int:
    """How many of the persona's interests this agent covers.

    Counting distinct interests rather than matching agent entries matters for
    prose fields: the Policy Q&A agent lists two separate use cases about
    policy, and counting entries scored that interest twice, rewarding a wordy
    listing over a precise one. Breadth of coverage is the honest measure.

    Matching tolerates wording differences between two catalogues -- exact
    equality missed "Sanctions screening" against "Sanctions list screening" --
    by treating a phrase as matched when one side's significant words are a
    subset of the other's. That stays tight enough that "Customer
    communication" does not match "Customer onboarding".
    """
    have = [h for h in (set(tokens(v)) for v in agent_values) if h]
    covered = 0
    for target in wanted:
        want = set(tokens(target))
        if want and any(h <= want or want <= h for h in have):
            covered += 1
    return covered


def curation_breakdown(agent: Agent, persona: Persona | None) -> dict[str, float]:
    """Per-component curation score, so any ranking can be explained."""
    popularity = agent.popularity / 100
    if persona is None:
        return {"domain": 0.0, "capability": 0.0, "use_case": 0.0, "tag": 0.0,
                "persona_boost": 0.0, "popularity": popularity}
    interests = persona.interests
    # What the agent is for, in the owner's own words. A use case counts when it
    # actually covers one of the persona's interests, which catches agents whose
    # capability list is thin but whose described purpose is squarely relevant.
    wanted = interests.capabilities + interests.tags
    evidence = {
        "domain": CURATION_WEIGHTS["domain"] * _covered(agent.business_domains, interests.domains),
        "capability": CURATION_WEIGHTS["capability"] * _covered(agent.capabilities, interests.capabilities),
        "use_case": CURATION_WEIGHTS["use_case"]
        * min(_covered(agent.use_cases, wanted), USE_CASE_CAP),
        "tag": CURATION_WEIGHTS["tag"] * _covered(agent.tags, interests.tags),
    }
    targeted = persona.id in agent.personas
    boost = sum(evidence.values()) * PERSONA_BOOST if targeted else 0.0
    return {**evidence, "persona_boost": round(boost, 2), "popularity": popularity}


def curation_score(agent: Agent, persona: Persona | None) -> float:
    return sum(curation_breakdown(agent, persona).values())


def recommend_for_persona(persona: Persona | None, agents: list[Agent], limit: int = 8) -> list[Agent]:
    """Persona curation for the 'Recommended for you' carousel.

    Static: derived persona + agent metadata. No behavioural signals.
    """
    if persona is None:
        return sorted(agents, key=lambda a: -a.popularity)[:limit]

    ranked = sorted(agents, key=lambda a: -curation_score(a, persona))
    return [a for a in ranked if curation_score(a, persona) >= 1][:limit]
