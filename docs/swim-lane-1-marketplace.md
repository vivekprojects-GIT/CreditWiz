# Swim Lane 1: AI Marketplace & Discovery

First deliverable for review with Ganesh. Scope follows the brief: make the ~10 real agents visible, searchable, understandable and actionable with very little friction. No integrations, no vector platform, no dynamic personalisation.

## What is built

| # | Ask | Where it lives | Status |
| --- | --- | --- | --- |
| 1 | Real agent list | `backend/data/agents.json` | 10 **sample** agents in the agreed shape (KYC Document Verifier, KYC Risk Screening, Contract Analyzer, Asset Locator, and six more). Replace with the list from Ganesh / Vinay. |
| 2 | Agent metadata template | `docs/agent-metadata-template.md`, `backend/data/agent-metadata-template.json`, also served at `GET /api/marketplace/metadata-template` | Done. Seven groups: Identity, Business, Capabilities, Technical, Governance, Resources, Lifecycle. Owners can also send the simple flat format. |
| 3 | Agent Discovery landing page | `/marketplace` | Done. Generative search on top, Netflix-style carousels below. |
| 4 | Generative / NLP search | `POST /api/marketplace/search`, `backend/app/marketplace/search.py` | Done. Understands intent, matches metadata, ranks, explains why. |
| 5 | Netflix-style carousels | `backend/data/carousels.json` | Done. Recommended for you, Compliance & Risk, Document Intelligence, Customer Operations, Popular & featured, Developer Tools. |
| 6 | Persona-based categorisation | `backend/data/personas.json`, persona picker on the page | Done. Five predefined personas. Recommended carousel and search ranking change with persona. |
| 7 | Agent detail page | `/marketplace/agents/{id}` | Done. One page: what it is, what it does, who it is for, owner, tools and models, access, docs, architecture, related agents. |
| 8 | Actions | Detail page header and sidebar | Launch, Request access, Documentation, Architecture pattern, Collaborate with owner, Email owner. |
| 9 | "Did you find what you need?" | Under search results and on every detail page | Done. Yes / No, and "tell us what was missing" on No. Stored in `backend/var/feedback.jsonl`. |

Also real, so the demo journey never dead-ends:

- **Documentation and architecture in the hub.** Every agent has an in-app documentation page (`/marketplace/agents/{id}/docs`, markdown from `backend/data/docs/{id}.md`) and an architecture pattern page (`/architecture`, from `backend/data/architecture/{pattern}.md`). The original external links stay available as "Source".
- **Related learning on every agent, owned by the Learning pillar.** The agent page consumes `GET /api/learning/for-agent/{id}`; the Learning pillar owns the content and the recommendation logic. Swim Lane 1 does not implement a learning recommender. Each opens the exact video at `/learning/videos/{id}?from={agent}` with a working player, "Up next", the agents covered, and a **Back to {agent}** button. The Learning pillar itself is a real catalogue filtered by path.
- **Back everywhere.** Agent, docs, architecture and video pages carry a Back control that returns to the previous in-app page (search results keep their query because it lives in the URL) or to a sensible parent when the page was opened directly.
- Videos are real, public YouTube sessions from IBM Technology, AWS Developers, Google Cloud, GitHub, CAMS, RapidAML, Litera, Webio and FinCrime Agent, embedded with the privacy-enhanced player and credited on the page. When the MUFG AI Hub records its own sessions, replace `youtube_id` per entry, or set `video_url` for an internally hosted file.

Also included, because the brief asked for scaffolding only:

- **Footprints go to a shared hub layer, not to this pillar.** Interaction events and feedback are written to `POST /api/context/events` and `/api/context/feedback`, owned by the AI Hub and used by every pillar. Swim Lane 1 is one producer among nine; Learning already writes to the same store. Nothing reads it for ranking. See [shared-user-context.md](shared-user-context.md).
- **No-match path.** When nothing matches, the page offers "Submit an intake request", "Learn how to build an agent" and "Ask the community".

## What is deliberately not built

Cross-pillar personalisation is a horizontal hub capability, not part of this lane. Also out: Agent 365, AWS Agent Registry, GitHub, Confluence, prompt store and skill store integrations. Vector database. Dynamic behavioural personalisation. Cross-pillar recommendations. Super Agent. Full collaboration workflow (the "Collaborate with owner" action links into the Community pillar and stops there).

## Data source: static JSON metadata

```text
Agent list from Ganesh / Vinay
        ↓
Common metadata template            docs/agent-metadata-template.md
        ↓
Populate agent metadata
        ↓
agents.json                         backend/data/agents.json
        ↓
Hub backend reads + validates       every record checked against the model
        ↓
Catalog · Persona filtering · Search · Agent detail
        ↓
Marketplace UI
```

**What to say on Friday:** for the MVP we use a static JSON-based metadata source containing the initial set of agents. This lets us focus on proving the discovery, search, curation and agent-detail experience without introducing integration dependencies. The data source can later be replaced by enterprise registries or other integrations without changing the user experience.

Two record shapes are accepted: the canonical template, and the simple intake format (`agentId`, `name`, `description`, `domain`, `useCases`, `capabilities`, `personas`, `platform`, `owner`, `status`, `tools`, `models`, `documentationUrl`, `architectureUrl`, `launchUrl`, `createdDate`, `updatedDate`). `backend/app/marketplace/store.py` normalises both, so agent owners can fill whichever is easier.

## Discovery and curation

How "Recommended for you", search, related agents and related learning rank things is written up in [discovery-and-curation.md](discovery-and-curation.md). One distinction matters when presenting it: **the client requirement is persona-based discovery now with behavioural personalisation later; the four scoring mechanisms and their weights are our implementation design.**

The "Recommended for you" ordering is a **curation score**, not a learned model, so every position is explainable. `GET /api/marketplace/curation` returns the per-component breakdown.

## How search works

```text
"I need an agent that can review customer onboarding documents"
        ↓
Understand intent   → summary, concepts, domains, capabilities, keywords
        ↓
Match metadata      → weighted fields: name, use cases, capabilities, domains, tags, category, description
        ↓
Rank                → direct-term boost, persona boost, status penalty, drop long tail
        ↓
Explain             → "Why this matched: This agent supports review customer onboarding documents; covers document extraction and identity verification; works in Onboarding and Compliance."
```

Intent understanding has two engines behind one interface:

- **Claude** when `ANTHROPIC_API_KEY` is set (in `backend/.env`). The request goes to `claude-sonnet-5` by default (about 3 seconds; `CREDITWIZ_SEARCH_MODEL=claude-opus-5` is more thorough but takes about 30 seconds) with a structured output schema (`SearchIntent`). The UI shows "Interpreted by Claude".
- **Local lexicon** otherwise. A concept lexicon (onboarding / KYC, AML screening, contracts, disputes, collections, asset tracing, policy, communication, engineering, and so on) expands the query. The UI shows "Interpreted locally".

Final relevance = semantic match (intent concepts and expanded keywords) + keyword match (direct terms) + metadata match (domain, capability, persona). Any Claude failure falls back to the local engine, so the demo never breaks. With ten agents this runs in microseconds and needs no vector database. When the catalogue grows, embeddings over the same searchable text (name, description, domain, use cases, capabilities, personas, tags) slot into the `SearchIntent -> ranked matches` seam.

Set `CREDITWIZ_DISABLE_LLM=1` to force the local engine even when a key is present.

## How persona discovery works

```text
Persona (business_user | compliance_user | risk_analyst | operations_user | developer)
        ↓
Interests: domains, capabilities, tags   (personas.json)
        ↓
Recommended for you: agents built for the persona first, then interest overlap, then popularity
Search: +20% for agents built for the persona, +5% per interest overlap
```

The persona is **derived, not stored**. The signed-in directory-style profile (stored in SQLite; development seeds include `backend/data/user.json`, standing in for Active Directory) carries name, job title, department, business unit, location, manager and groups, but no persona field. `backend/app/identity.py` derives it with `backend/data/persona-mapping.json`:

```text
Directory profile: Role = "Compliance Analyst", Department = "Compliance"
        ↓
Persona mapping (exact title → title contains → department → business unit → default)
        ↓
Persona = Compliance User
        ↓
Curation: Recommended carousel, search boosts, learning picks
```

The marketplace shows "Sai Vivek · Role: Compliance Analyst · Persona: Compliance User · derived from job title". A **Preview as…** control lets a demo switch persona without touching the profile; it is clearly marked and one click returns to the derived persona. When Active Directory is connected, only `load_profile()` changes.

## What we need from Ganesh / Vinay

1. The real agent list (name, description, any existing metadata), ideally as the template filled in.
2. Confirmation of the persona list and labels. The five here are placeholders shaped on the ones mentioned in the meeting.
3. The category names to use for carousels (currently: Compliance & Risk, Document Intelligence, Customer Operations, Knowledge & Policy, Developer Tools).
4. Whether an LLM endpoint is available for the demo. Not required, but it makes the "interpreted by" step visibly generative.

## Review flow

```text
Receive agent list → replace agents.json → show Ganesh → feedback → improve → later show Raja / Prasad
```
