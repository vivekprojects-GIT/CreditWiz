# Discovery and Curation — how the MVP ranks things

**Read this distinction first.**

| | |
| --- | --- |
| **Client requirement** | Persona-based discovery now; behavioural, cross-pillar personalisation later. |
| **Our implementation design** | The four scoring mechanisms below, the weights, and the `/api/context/*` seam. These are our choices, not things that were asked for. Change them freely. |

Everything in this document except the top row is implementation design.

## Current MVP

```text
User Role
   ↓
Derived Persona
   ↓
Persona Curation Rules
   ↓
Agent Metadata
   ↓
Recommended for You


User Natural-Language Search
   ↓
Intent Understanding
   ↓
Metadata Search
   ↓
Persona Boost
   ↓
Search Results


Agent Selected
   ↓
Metadata Similarity
   ↓
Related Agents


User Activity
Search / Click / View / Launch / Learning
   ↓
Footprints Collected
   ↓
Stored for Future Use
   ✗
Does NOT influence current ranking
```

## 1. Recommended for you — persona curation

A **curation score**, not a recommendation model. Rule-based on purpose so any position can be justified in review.

```text
domain match        +3 each
capability match    +2 each
use-case match      +2 each  (capped at 3)
tag match           +1 each
                    ─────────
persona named       +25% of the above, when the owner names this persona
popularity          tie-breaker
```

Every dimension counts **distinct persona interests covered**, not matching
entries on the agent. That matters for prose: the Policy Q&A agent lists two
separate use cases about policy, and counting entries scored that interest
twice, lifting it above better-matched agents on wordiness alone.

Relevance is **derived from business metadata**. An owner describes what the
agent does; they do not enumerate every role that might want it. An agent that
names no persona at all still ranks on its domains, capabilities and tags.

`personas` is therefore an optional curator hint, and it is deliberately a
percentage rather than a flat score: 25% of no matched metadata is nothing, so
a mistaken persona tag cannot promote an unrelated agent. An earlier version
awarded a flat +10, which outvoted the evidence — Contract Analyzer, with one
domain match and no capability or tag overlap, scored 13.88 against the Dispute
Resolution Agent's 3.77 on identical evidence, purely because someone had typed
a persona onto it. It now scores 4.63 against 3.77.

Phrase matching tolerates wording differences between two catalogues:
"Sanctions screening" matches "Sanctions list screening", because one side's
significant words are a subset of the other's. It stays tight enough that
"Customer communication" does not match "Customer onboarding".

`GET /api/marketplace/curation` returns the full breakdown, so "why is KYC Risk Screening first?" has a direct answer:

| Agent | Domain | Capability | Use case | Tag | Persona boost | Total |
| --- | --- | --- | --- | --- | --- | --- |
| KYC Risk Screening | 9 | 6 | 4 | 3 | 5.5 | 28.31 |
| KYC Document Verifier | 6 | 4 | 2 | 1 | 3.25 | 17.17 |
| Policy Q&A | 3 | 2 | 4 | 2 | 2.75 | 14.70 |

## Two ranking modes, two different questions

```text
RECOMMENDED FOR YOU          SEARCH
"who are you?"               "what do you need right now?"
persona drives it            query intent drives it
                             persona is a x1.2 nudge at most
```

A compliance user searching *"I need something to review Python code"* gets the
Code Review Assistant, not KYC. A test pins that.

Code: `curation_breakdown()` and `recommend_for_persona()` in `backend/app/marketplace/search.py`.

## 2. Search — a different question

Recommendation asks *given who this user is, what should we proactively surface?*
Search asks *given what the user just asked for, what satisfies this need?*

```text
Natural-language query
        ↓
Intent understanding      Claude when a key is set, local lexicon otherwise
        ↓
Agent metadata matching   name, use cases, capabilities, domains, tags, category, description
        ↓
Semantic / lexical relevance
        ↓
Small persona boost       ×1.2 built-for, ×1.05 domain, ×1.05 capability
        ↓
Ranked results + "why this matched"
```

The persona multipliers are deliberately modest so **intent dominates**. A compliance user searching "agent that helps generate Python code" gets the Code Review Assistant, not a KYC agent.

## 3. Related agents — metadata similarity

```text
Current Agent → category, domains, capabilities, tags → similar agents
```

Three points for the same category, two per shared domain, one per shared capability. Fine for ten agents.

## 4. Learning curation — owned by the Learning pillar

Full write-up: [learning-pillar.md](learning-pillar.md). Learning also tracks progress, which the Marketplace does not.

The Marketplace does **not** own a learning recommender. It consumes one.

```text
Agent Detail Page  (Marketplace)
        ↓  consumes
GET /api/learning/for-agent/{agent_id}?persona=
        ↓
Learning pillar owns the content AND the recommendation logic
```

Learning applies the same explainable curation idea the Marketplace uses for agents, over its own metadata. A `persona_paths` map in `backend/data/learning.json` says which paths matter to which persona.

**Learning's own "Recommended for you" row** (`GET /api/learning/recommended`):

```text
path affinity      +10 / +6 / +3   by position in the persona's path list
persona tag match  +2 each
```

**On an agent page**, agent relevance must dominate so the right content always appears; persona only re-orders among videos that already teach that agent:

```text
explicit agent link  +10
agent tag overlap    +2 each
persona affinity     +5 / +3 / +1   (re-ordering nudge only)
```

Same agent, different persona:

| Persona | 1st | 2nd |
| --- | --- | --- |
| Compliance user | How Banks Know Who You Are (compliance) | Amazon Bedrock for Beginners (builders) |
| Developer | Amazon Bedrock for Beginners (builders) | How Banks Know Who You Are (compliance) |

`GET /api/learning/curation` returns the per-component breakdown, as the marketplace one does.

**Naming.** The agent page section is "Learning for this agent", because that is what it is: content linkage, persona-ordered. "Recommended for you" is reserved for the persona-curated row in Learning.

## What footprints do today

```text
Searches · Clicks · Agent views · Launches · Learning views · Feedback
        ↓
POST /api/context/events        (shared hub layer, every pillar)
        ↓
backend/var/interactions.jsonl
        ↓
Stored. Read by nothing that ranks.
```

Recommendations currently depend on the **derived persona and static agent metadata**. They also change when an agent's capabilities, domains, tags or popularity change, when an agent is added or removed, or when the persona mapping changes. Behavioural footprints do not affect ranking.

## Future

```text
Role / Persona
      +
Cross-Pillar Footprints
      +
Derived User Interests
        ↓
Adaptive Curation
        ↓
Personalized Marketplace
        ↓
Personalized Learning
        ↓
Eventually broader AI Hub / Super Agent
```

The transition would become:

```text
Future score = Persona Score + Metadata Relevance + User Interest Overlap
```

`GET /api/context/interests` already aggregates topics across pillars and is **our implementation seam**, added to make that transition cheap. It was not a client request, and nothing reads it for ranking. Wiring it in means adding one interest-overlap term to `curation_breakdown()` and to the search multipliers.
