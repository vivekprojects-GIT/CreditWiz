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
from collections import defaultdict

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
    (("sanction", "sanctions", "pep", "aml", "screen", "screening", "money laundering", "due diligence"),
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
    q = " " + query.lower() + " "
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

_FIELD_WEIGHTS = {
    "name": 6.0,
    "tagline": 3.0,
    "use_cases": 4.0,
    "capabilities": 3.5,
    "business_domains": 3.0,
    "tags": 3.0,
    "category": 2.0,
    "description": 1.5,
}


def _fields(agent: Agent) -> dict[str, str]:
    return {
        "name": agent.name,
        "tagline": agent.tagline,
        "use_cases": " ".join(agent.use_cases),
        "capabilities": " ".join(agent.capabilities),
        "business_domains": " ".join(agent.business_domains),
        "tags": " ".join(agent.tags),
        "category": agent.category,
        "description": agent.description,
    }


def _term_weights(query: str, intent: SearchIntent) -> dict[str, float]:
    weights: dict[str, float] = defaultdict(float)
    for t in tokens(query):
        weights[t] += 1.0
    for kw in intent.keywords:
        for t in tokens(kw):
            weights[t] += 0.6
    for cap in intent.capabilities:
        for t in tokens(cap):
            weights[t] += 0.5
    for dom in intent.domains:
        for t in tokens(dom):
            weights[t] += 0.5
    return weights


def rank(
    query: str,
    intent: SearchIntent,
    agents: list[Agent],
    persona: Persona | None = None,
    domain: str | None = None,
    limit: int = 6,
) -> list[AgentMatch]:
    term_weights = _term_weights(query, intent)
    if not term_weights:
        return []
    query_terms = set(tokens(query))
    matches: list[AgentMatch] = []

    for agent in agents:
        if domain and domain not in agent.business_domains:
            continue
        score = 0.0
        hits: dict[str, set[str]] = defaultdict(set)
        for field, text in _fields(agent).items():
            field_tokens = tokens(text)
            if not field_tokens:
                continue
            counts: dict[str, int] = defaultdict(int)
            for t in field_tokens:
                counts[t] += 1
            for term, w in term_weights.items():
                if term in counts:
                    tf = 1.0 + 0.3 * min(counts[term] - 1, 3)
                    score += w * _FIELD_WEIGHTS[field] * tf
                    hits[field].add(term)
        if score <= 0:
            continue

        # Direct query-term hits matter more than expansion hits.
        direct = {t for s in hits.values() for t in s if t in query_terms}
        score *= 1.0 + 0.15 * len(direct)

        # Persona boost, deliberately modest: search INTENT must dominate. A compliance
        # user searching for code help should still get the code agent first.
        if persona:
            if persona.id in agent.personas:
                score *= 1.2
            interests = persona.interests
            if any(d in interests.domains for d in agent.business_domains):
                score *= 1.05
            if any(c in interests.capabilities for c in agent.capabilities):
                score *= 1.05

        if agent.status == "deprecated":
            score *= 0.5

        reasons = _reasons(agent, hits, intent, persona)
        matches.append(AgentMatch(agent=agent, score=round(score, 2), why=_why(agent, hits, intent, persona), reasons=reasons))

    matches.sort(key=lambda m: (-m.score, -m.agent.popularity))
    if not matches:
        return []
    # Drop long-tail noise: keep anything within 35% of the best score.
    best = matches[0].score
    return [m for m in matches if m.score >= best * 0.35][:limit]


def _join(items: list[str]) -> str:
    items = [i for i in items if i]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]


def _why(agent: Agent, hits: dict[str, set[str]], intent: SearchIntent, persona: Persona | None) -> str:
    """One plain sentence explaining the match, built from the metadata that matched."""
    use_terms = hits.get("use_cases", set())
    use_case = next((u for u in agent.use_cases if use_terms & set(tokens(u))), None)
    caps = [c for c in agent.capabilities if c in intent.capabilities or set(tokens(c)) & hits.get("capabilities", set())][:3]
    domains = [d for d in agent.business_domains if d in intent.domains or set(tokens(d)) & hits.get("business_domains", set())][:2]
    parts: list[str] = []
    if use_case:
        parts.append(f'supports "{use_case}"')
    if caps:
        parts.append("covers " + _join([c.lower() for c in caps]))
    if domains:
        parts.append("works in " + _join(domains))
    sentence = f"This agent {', '.join(parts)}." if parts else f"{agent.name} matches the terms in your request."
    if persona and persona.id in agent.personas:
        sentence += f" It is built for {persona.label.lower()}s."
    return sentence


def _reasons(agent: Agent, hits: dict[str, set[str]], intent: SearchIntent, persona: Persona | None) -> list[str]:
    reasons: list[str] = []
    if "use_cases" in hits:
        terms = hits["use_cases"]
        uc = next((u for u in agent.use_cases if terms & set(tokens(u))), None)
        if uc:
            reasons.append(f'Use case: "{uc}"')
    cap_hits = [c for c in agent.capabilities if c in intent.capabilities or set(tokens(c)) & hits.get("capabilities", set())]
    if cap_hits:
        reasons.append("Capabilities: " + ", ".join(cap_hits[:3]))
    dom_hits = [d for d in agent.business_domains if d in intent.domains or set(tokens(d)) & hits.get("business_domains", set())]
    if dom_hits:
        reasons.append("Domain: " + ", ".join(dom_hits))
    if persona and persona.id in agent.personas:
        reasons.append(f"Built for {persona.label.lower()}s")
    if not reasons and hits:
        reasons.append("Matches " + ", ".join(sorted({t for s in hits.values() for t in s})[:4]))
    return reasons[:4]


# --- curation ---------------------------------------------------------------
# MVP implementation design (ours, not a client requirement): a transparent,
# explainable curation score. Deliberately rule-based, not a learned model, so
# every position in "Recommended for you" can be justified in review.
#
#   persona match  +10 | domain match  +3 each
#   capability     +2 each | tag match +1 each | popularity = tie-breaker
#
# Inputs are the derived persona and static agent metadata ONLY. Behavioural
# footprints (app/context) are collected but deliberately not read here.

CURATION_WEIGHTS = {"persona": 10.0, "domain": 3.0, "capability": 2.0, "tag": 1.0}


def curation_breakdown(agent: Agent, persona: Persona | None) -> dict[str, float]:
    """Per-component curation score, so any ranking can be explained."""
    if persona is None:
        return {"persona": 0.0, "domain": 0.0, "capability": 0.0, "tag": 0.0, "popularity": agent.popularity / 100}
    return {
        "persona": CURATION_WEIGHTS["persona"] if persona.id in agent.personas else 0.0,
        "domain": CURATION_WEIGHTS["domain"] * len(set(agent.business_domains) & set(persona.interests.domains)),
        "capability": CURATION_WEIGHTS["capability"] * len(set(agent.capabilities) & set(persona.interests.capabilities)),
        "tag": CURATION_WEIGHTS["tag"] * len(set(agent.tags) & set(persona.interests.tags)),
        "popularity": agent.popularity / 100,
    }


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
