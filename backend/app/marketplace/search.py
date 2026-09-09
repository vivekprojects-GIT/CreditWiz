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

from . import semantic
from .models import Agent, AgentMatch, Persona, SearchIntent

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
# Typed search is semantic retrieval over the agent metadata. The request --
# enriched with what we understood from it -- is embedded once and compared
# with every agent's embedded description; results are ordered by similarity.
#
# Deliberately absent: per-field lexical weights, popularity, persona
# multipliers and a blend between two rankers. Each grew for a reason, and
# together they were four tuning knobs explaining one ordering. The
# Recommended-for-you carousel keeps its arithmetic (curation, below) because
# that per-component table is a review asset; a typed query does not need it.

# Cosine has no notion of "nothing else is relevant" -- it always fills top-K,
# so without a floor a sanctions query lists the Asset Locator. Two floors:
# an absolute one, and a relative one against the best hit, because a strong
# top result makes a 0.47 look like noise where a weak one would not. Measured
# on this catalogue with the enriched query: real matches 0.54-0.85, noise
# 0.35-0.47. Model-dependent: retune if the embedding model changes.
SIMILARITY_FLOOR = 0.45
RELATIVE_FLOOR = 0.65


def retrieval_text(query: str, intent: SearchIntent) -> str:
    """The text that gets embedded for retrieval.

    Bare words embed weakly: "code" alone lands at 0.26 against the Code Review
    Assistant, under the floor. Folding in what we understood -- the summary,
    domains and capabilities -- is query expansion done once, before the single
    retrieval. Understanding informs the search; it does not rank it.
    """
    parts = [
        query.strip(),
        intent.summary,
        ", ".join(intent.domains),
        ", ".join(intent.capabilities),
    ]
    return ". ".join(part for part in parts if part)


def _fallback(query: str, intent: SearchIntent, agents: list[Agent]) -> dict[str, float]:
    """Used ONLY when the index is unavailable.

    Shared-token overlap between the enriched request and each agent's
    embedding text, so a broken or switched-off index still finds agents.
    This is resilience, not ranking design, and it is not tuned.
    """
    wanted = set(tokens(retrieval_text(query, intent)))
    if not wanted:
        return {}
    found: dict[str, float] = {}
    for agent in agents:
        shared = len(wanted & set(tokens(semantic.embedding_text(agent))))
        if shared:
            found[agent.id] = shared / len(wanted)
    return found


def rank(
    query: str,
    intent: SearchIntent,
    agents: list[Agent],
    persona: Persona | None = None,
    domain: str | None = None,
    limit: int = 6,
    similar: dict[str, float] | None = None,
) -> list[AgentMatch]:
    """`similar` lets the caller pass a retrieval it already ran. Embedding the
    query is the expensive step, and the router does it once for both the
    ranking and the trace rather than twice."""
    if similar is None and semantic.index.available:
        similar = semantic.index.search(retrieval_text(query, intent))
    if similar is not None:
        floor = SIMILARITY_FLOOR
    else:
        similar = _fallback(query, intent, agents)
        floor = 0.0  # overlap fractions sit on a different scale; keep any hit
    if not similar:
        return []

    # `agents` is already the caller's visible subset. The index is built from
    # the whole catalogue, so an agent this user may not see can be retrieved;
    # it is dropped here by construction and can never surface.
    by_id = {agent.id: agent for agent in agents}
    ordered = sorted(similar.items(), key=lambda kv: -kv[1])
    best = ordered[0][1]
    cutoff = max(floor, best * RELATIVE_FLOOR) if floor else 0.0
    matches: list[AgentMatch] = []
    for agent_id, similarity in ordered:
        agent = by_id.get(agent_id)
        if agent is None or similarity < cutoff:
            continue
        if domain and domain not in agent.business_domains:
            continue
        matches.append(
            AgentMatch(
                agent=agent,
                score=round(similarity, 3),
                why=_why(agent, intent, persona),
                reasons=_reasons(agent, intent, persona),
                coverage=_coverage(agent, intent),
            )
        )
    return matches[:limit]


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
