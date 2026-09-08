# API reference

Every endpoint in the hub. Overview and screenshots are in the [README](../README.md).

## Endpoints

| Endpoint | Purpose |
| --- | --- |
| `GET /api/home` | Current user, business domains, the nine pillars with their sections |
| `GET /api/me` | Current user from the mocked directory profile (`backend/data/user.json`) with the persona derived via `persona-mapping.json` |
| `GET /api/pillars` | Pillars visible to the current user (admin-only pillars filtered) |
| `GET /api/pillars/{id}` | One pillar with its sections, 404 if hidden or unknown |
| `GET /api/notifications` | Notifications for the current user |
| `GET /api/domains` | Business domain filter options |
| `GET /api/search?q=` | Search across solutions, agents, prompts and learning |
| `GET /api/health` | Liveness |
| `GET /api/marketplace/home?persona=` | Personas, domains and persona-ranked carousels |
| `GET /api/marketplace/agents` | All agents, filter by `domain`, `category`, `persona`, `status` |
| `GET /api/marketplace/agents/{id}` | One agent's full metadata (`/related` for similar agents) |
| `POST /api/marketplace/search` | Natural-language search: `{query, persona?, domain?}` |
| `POST /api/context/events` | Interaction footprints from **any** pillar (shared hub layer) |
| `POST /api/context/feedback` | "Did you find what you needed?" from any pillar |
| `GET /api/context/me` | Profile, derived persona and derived interests in one place |
| `GET /api/context/interests` | Weighted topic signals aggregated across pillars |
| `GET /api/context/summary` | Event and feedback counts by pillar |
| `GET /api/marketplace/curation` | Per-component curation score for every agent (explainable ranking) |
| `GET /api/learning/for-agent/{id}?persona=` | Content that teaches an agent, persona-ordered (Learning-owned) |
| `GET /api/learning/curation` | Per-component learning curation score (explainable) |
| `GET /api/marketplace/metadata-template` | The agent metadata template to hand to agent owners |
| `GET /api/marketplace/agents/{id}/docs` | In-app documentation page (markdown from `backend/data/docs`) |
| `GET /api/marketplace/agents/{id}/architecture` | Architecture pattern page (markdown from `backend/data/architecture`) |
| `GET /api/marketplace/agents/{id}/learning` | Recommended videos for the agent |
| `GET /api/learning?persona=` | Role-based learning landing sections |
| `GET /api/learning/items` | Learning items of any type, filterable |
| `GET /api/learning/items/{id}` | One item with related items and agents |
| `POST /api/learning/progress` | Record started / in progress / completed |
| `GET /api/learning/my-learning` | Progress counts and topic coverage |

## Marketplace (Swim Lane 1)

The MVP metadata source is a static JSON file: `backend/data/agents.json` (personas in `personas.json`, carousel definitions in `carousels.json`). Records may use the canonical template or the simple camelCase intake format; both are normalised on load. See [docs/agent-metadata-template.md](docs/agent-metadata-template.md). Point `CREDITWIZ_DATA_DIR` at another directory to swap the source. Copy `backend/.env.example` to `backend/.env` and set `ANTHROPIC_API_KEY` to have Claude interpret search requests (`CREDITWIZ_SEARCH_MODEL` picks the model, default `claude-sonnet-5`); without a key a local lexicon does the job. Footprints and feedback are hub-wide, not pillar-owned: every pillar posts to `/api/context/*` and they land in `backend/var/interactions.jsonl` and `feedback.jsonl`. Architecture: [docs/shared-user-context.md](docs/shared-user-context.md). Ranking and curation: [docs/discovery-and-curation.md](docs/discovery-and-curation.md). Learning pillar: [docs/learning-pillar.md](docs/learning-pillar.md). Full write-up: [docs/swim-lane-1-marketplace.md](docs/swim-lane-1-marketplace.md).

## Routes

`/` home, `/help`, `/settings`, and one route per pillar (`/marketplace`, `/library`, `/learning`, `/intake`, `/governance`, `/knowledge`, `/community`, `/insights`, `/platform`) with section sub-routes such as `/learning/catalog`. The marketplace has real pages: `/marketplace`, `/marketplace/agents`, `/marketplace/agents/{id}`, plus `/docs` and `/architecture` under each agent. Learning is real too: `/learning?path=...` and `/learning/videos/{id}`. Unknown paths show a not-found page.

Hub content lives in `backend/app/data.py`. Replace it with a real store when the marketplace, learning and community services exist.
