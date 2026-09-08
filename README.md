# CreditWiz — Enterprise AI Hub

Swim Lane 1 prototype: **AI Marketplace & Discovery**, plus a working **Learning** pillar and the shared hub layer both sit on.

React frontend, all-Python backend. Ten sample agents, twenty-two learning items, no external integrations.

---

## Read this first

| | |
| --- | --- |
| **Client requirement** | Persona-based discovery now. Relevant, authorised learning for the role, with progress measured. Behavioural, cross-pillar personalisation later. |
| **Our implementation design** | The metadata template, the curation weights, the landing sections, the storage split, and the `/api/context/*` seam. Ours to change, not things that were asked for. |
| **Deliberately not decided by us** | **Proficiency.** The hub displays learning progress and topic coverage. Proficiency remains a separate capability until the agreed enterprise measure is defined. |

For the MVP the metadata source is a **static JSON file**. That keeps the prototype focused on proving discovery, search, curation and the agent-detail experience without integration dependencies. The source can later be replaced by enterprise registries without changing the user experience.

---

## Walkthrough

### 1. Home — one hub, nine pillars

![Home](docs/screenshots/01-home.png)

Persona-picked agents and what's new sit under the three priority modules. The persona is **derived** from the directory profile, never stored on it.

### 2. Marketplace — describe what you need

![Marketplace](docs/screenshots/02-marketplace.png)

Two discovery paths, as discussed: generative search at the top, Netflix-style carousels below. The Recommended row carries a visible persona badge and a demo-only "preview as".

### 3. Generative search — and why it matched

![Search results](docs/screenshots/03-search.png)

> *"I need something for validating customer documents during onboarding"*

Claude interprets the request into concepts — document validation, onboarding compliance, identity verification — then the ranker matches those against agent metadata. Every result explains itself:

> **Why this matched:** This agent supports "Review customer onboarding documents for completeness", covers document extraction, identity verification and completeness checking, works in Onboarding and Compliance. It is built for compliance users.

No key configured? A local concept lexicon does the same job and the badge reads "Interpreted locally". The demo never breaks.

### 4. Agent detail — understand, then act

![Agent detail](docs/screenshots/04-agent-detail.png)

One page answers what it is, why it exists, what to ask it, who owns it, what it runs on, and how to get access. Actions: Launch, Request access, Documentation, Architecture pattern, Collaborate with the owner. Related learning is consumed from the Learning pillar.

### 5. Documentation lives in the hub

![Agent documentation](docs/screenshots/07-agent-docs.png)

Every agent has real in-app documentation and an architecture pattern page. No dead links in the demo.

### 6. Learning — the right content for the role

![Learning](docs/screenshots/05-learning.png)

Required for your role first, then Continue learning, Recommended, Best practices, Documentation and guides, Quick references. Content is not just video: courses, Confluence pages, guides and one-pagers all appear.

### 7. My Learning — progress, not proficiency

![My learning](docs/screenshots/06-my-learning.png)

Completed, in progress, not started, and required progress. Topic coverage is shown as **counts** ("KYC 1 of 3"), never a percentage dressed up as proficiency. The note on the page states that explicitly.

### 8. The full catalogue

![All agents](docs/screenshots/08-all-agents.png)

---

## What was asked for, and where it is

| # | Ask | Status |
| --- | --- | --- |
| 1 | Real agent list | 10 **sample** agents in the agreed shape. Replace `backend/data/agents.json` with the real list. |
| 2 | Agent metadata template | [docs/agent-metadata-template.md](docs/agent-metadata-template.md). Seven groups. The simple flat format is accepted too. |
| 3 | Discovery landing page | `/marketplace` |
| 4 | Generative / NLP search | Claude or local lexicon, with explanations |
| 5 | Netflix-style carousels | Six, from `backend/data/carousels.json` |
| 6 | Persona-based curation | Five personas, derived from job title |
| 7 | Agent detail page | Low friction, one page |
| 8 | Actions | Launch · Access · Docs · Architecture · Collaborate |
| 9 | "Did you find what you needed?" | Under search and on every detail page |

**Deliberately not built:** Agent 365, AWS Agent Registry, GitHub, Confluence ingestion, prompt and skill store integrations, a vector database, dynamic personalisation, Super Agent, cross-pillar recommendations.

---

## How ranking works

Four separate mechanisms, all rule-based and explainable. Full detail in [docs/discovery-and-curation.md](docs/discovery-and-curation.md).

**Recommended agents** — a curation score, not a learned model:

```text
persona match  +10 | domain +3 each | capability +2 each | tag +1 each | popularity = tie-break
```

`GET /api/marketplace/curation` returns the per-component breakdown, so "why is KYC Risk Screening first?" has a direct answer.

**Search** asks a different question, so intent dominates and persona is only a ×1.2 nudge. A compliance user searching for code help gets the code agent.

**Related agents** is metadata similarity. **Related learning** is owned by the Learning pillar and consumed here.

**What none of them use:** searches, clicks, views, launches and completions are all collected, and none of it feeds ranking. That stays future work.

---

## Architecture

```text
                              AI HUB
 ┌──────────┬──────────┬────────┴─────┬──────────┬──────────┐
Marketplace Learning  Community    Prompts    Skills    other pillars…
 └──────────┴──────────┴──────┬───────┴──────────┴──────────┘
                              ▼
                  SHARED USER CONTEXT LAYER
              ┌───────────────┴───────────────┐
       User Profile                    User Footprints
       Role · Persona (derived)        Searches · Views · Launches
       Department · Business Unit      Learning activity · Feedback
              └───────────────┬───────────────┘
                              ▼
                     Curation / Ranking
                              ▼
                Personalised AI Hub Experience
```

Each pillar owns its experience. The hub owns shared user context, interaction data and, eventually, cross-pillar personalisation. Nothing about footprints lives inside a pillar. See [docs/shared-user-context.md](docs/shared-user-context.md).

**Persona is derived, never stored:**

```text
Directory profile (role, department, business unit)
        ↓  persona-mapping.json
Persona = Compliance User
        ↓
Curation
```

**Storage split** — the production shape:

| Data | Store | Why |
| --- | --- | --- |
| Learning progress | SQLite `backend/var/learning.db` | Mutable per-user state; needs atomic upsert |
| Footprints, feedback | JSONL `backend/var/*.jsonl` | Append-only event stream |
| Agents, learning, personas | JSON `backend/data/` | Authored, version-controlled, handed over |

---

## Run it

```bash
cd backend && uv run uvicorn app.main:app --reload --port 8000
```

```bash
cd frontend && npm install && npm run dev
```

Open http://localhost:5173.

Optional: copy `backend/.env.example` to `backend/.env` and add `ANTHROPIC_API_KEY` for Claude-interpreted search. Without it the local lexicon is used and everything still works.

```bash
cd backend && uv run pytest -q      # 32 tests
cd frontend && npm run build
```

---

## Branches

| Branch | Purpose |
| --- | --- |
| `main` | Reviewed, demo-ready. What Ganesh sees. |
| `dev` | Integration branch. Feature work merges here first. |
| `test` | QA and validation before promotion to `main`. |
| `end` | End-state / target-architecture spikes, including work explicitly out of MVP scope. |

Flow: `feature → dev → test → main`, with `end` as a parking place for future-state exploration.

---

## Layout

```text
backend/
  app/
    personas.py        hub-level personas (both pillars rank against these)
    identity.py        directory profile → derived persona
    context/           shared footprints + user context (all nine pillars)
    marketplace/       agents, search, curation, docs        ← Swim Lane 1
    learning/          content, curation, progress           ← Learning pillar
  data/                authored JSON: agents, learning, personas, mappings
  var/                 runtime state (git-ignored)
frontend/src/
  lib/context.ts       shared tracker every pillar calls
  components/marketplace/ · components/learning/
docs/                  the write-ups below
```

| Document | What it covers |
| --- | --- |
| [agent-metadata-template.md](docs/agent-metadata-template.md) | The template to hand to agent owners |
| [swim-lane-1-marketplace.md](docs/swim-lane-1-marketplace.md) | Scope, what is and is not built |
| [discovery-and-curation.md](docs/discovery-and-curation.md) | How everything is ranked |
| [learning-pillar.md](docs/learning-pillar.md) | Content model, sections, progress, proficiency line |
| [shared-user-context.md](docs/shared-user-context.md) | The horizontal hub layer |
| [api-reference.md](docs/api-reference.md) | Every endpoint |

---

## What we need next

1. The **real agent list** from Ganesh and Vinay. Name, brief description and any existing metadata is enough to start.
2. Confirmation of the **persona list** and labels.
3. Confirmation of the **category names** used for carousels.
4. The **agreed measure of proficiency**, when the business defines it.
