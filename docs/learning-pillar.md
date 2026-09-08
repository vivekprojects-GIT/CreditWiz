# Learning Pillar

**Read this distinction first.**

| | |
| --- | --- |
| **Client requirement** | Provide relevant, authorised learning for the employee's role, and measure progress and proficiency. |
| **Our implementation design** | The content model, the seven landing sections, the curation weights, and the progress store. These are our choices. |
| **Deliberately not decided by us** | **Proficiency.** For the MVP the hub displays learning progress and topic coverage. Proficiency will remain a separate capability until the agreed enterprise measure of proficiency is defined. |

Marketplace asks *which agent should I use?* Learning asks *what should I learn next, and where am I with it?* Same curation architecture, different output: agents versus content plus progress.

## Day 1 flow

```text
User profile / role
        ↓
Derived persona
        ↓
Static curation rules  +  learning metadata
        ↓
Relevant / authorised content
        ↓
LEARNING LANDING PAGE
        │
 ┌──────┼──────────┬───────────────┐
 │      │          │               │
Required  Continue  Recommended   Best practices ·
learning  learning  for your role  Docs · Quick refs
        ↓
Learning item
        ↓
Started / progress / completed
        ↓
My Learning
        ↓
Progress and topic coverage
```

## 1. Content model

One `items` collection, many types. `backend/data/learning.json`.

```json
{
  "id": "kyc-document-checklist",
  "title": "KYC document checklist",
  "type": "quick-reference",
  "description": "...",
  "topics": ["KYC", "Document AI"],
  "capabilities": ["Completeness checking"],
  "personas": ["compliance_user", "operations_user"],
  "required_for": ["compliance_user"],
  "path": "compliance",
  "duration_seconds": 240,
  "url": "",
  "body": "# markdown rendered in the hub"
}
```

Types: `video`, `course`, `confluence`, `guide`, `documentation`, `quick-reference`, `best-practice`. Currently 22 items across all seven.

Content is either **hub-native** (a `body` of markdown, rendered in place) or **external** (a `url`, opened in a new tab with a clear indication). Videos keep the click-to-play player.

## 2. Landing sections

Proposed UX, not a client-specified list. Sections only appear when they have content:

| Section | Rule |
| --- | --- |
| Required for your role | `required_for` contains the persona, not yet completed |
| Continue learning | status is `in_progress` |
| Recommended for your role | curation score, excluding completed and required |
| Best practices | type `best-practice` |
| Documentation and guides | type `documentation`, `guide` or `confluence` |
| Quick references | type `quick-reference` |

Path tabs (Getting started, Business users, Compliance and risk, Operations, Governance, Builders) remain as a second axis.

## 3. Curation

Learning-owned, same explainable idea the Marketplace uses for agents.

```text
path affinity      +10 / +6 / +3   by position in the persona's path list
persona tag match  +2 each
```

On an **agent page** the agent link must dominate, so persona is only a re-ordering nudge:

```text
explicit agent link  +10
agent tag overlap    +2 each
persona affinity     +5 / +3 / +1
```

`GET /api/learning/curation` returns the per-component breakdown.

## 4. Progress and coverage

Progress is **learning state**, not personalisation, so it is tracked from Day 1.

```text
User opens item      →  started (5%)
User plays / reads   →  in progress (n%)
User marks complete  →  completed (100%)
```

Status never regresses and progress never decreases. On completion Learning also emits a `learning_complete` footprint to the shared hub layer, so other pillars can see it.

**My Learning** shows completed, in progress, not started, required progress, and topic coverage as counts:

```text
Topic coverage
  Document AI     1 of 3
  KYC             1 of 3
  Governance      0 of 6
```

Never a percentage presented as proficiency. The page carries the proficiency note verbatim.

## Storage

The split is deliberate and is the production shape:

| Data | Store | Why |
| --- | --- | --- |
| Learning progress | **SQLite** (`backend/var/learning.db`) | Mutable per-user state with read-modify-write; needs atomic upsert and survives concurrent workers |
| Footprints | **JSONL** (`backend/var/interactions.jsonl`) | Append-only event stream, ships straight to analytics |
| Content, personas, mappings | **JSON files** (`backend/data/`) | Authored, version-controlled, handed to the client |

SQLite needs no server and is a single file. Swap `progress.py` for the enterprise store when there is one; the API does not change.

## What is deliberately held back

```text
✗ Behaviour changing recommendations
✗ Cross-pillar personalisation
✗ Learned user interests affecting ranking
✗ An invented proficiency score
```

Footprints and progress are both collected. Neither feeds ranking. Later:

```text
Role / Persona
      +
Learning behaviour
      +
Marketplace behaviour
      +
Other AI Hub footprints
        ↓
Adaptive curation
```

The cross-pillar example, completing several KYC learning items raising KYC agents in the Marketplace, is future and hub-owned.

## API

| Endpoint | Purpose |
| --- | --- |
| `GET /api/learning?persona=` | Role-based landing page sections |
| `GET /api/learning/items` | All items, filter by `path`, `type`, `topic`, `agent`, `status` |
| `GET /api/learning/items/{id}` | One item with related items and agents |
| `POST /api/learning/progress` | Record started / in progress / completed |
| `GET /api/learning/my-learning` | Progress counts and topic coverage |
| `GET /api/learning/for-agent/{id}?persona=` | Content that teaches an agent (consumed by the Marketplace) |
| `GET /api/learning/curation` | Per-component curation breakdown |
