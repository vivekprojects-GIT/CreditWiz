# Marketplace + Learning MVP

The implemented scope is Marketplace + Learning plus their shared account and persistence services. The nine-pillar navigation is retained; the other seven pillars are labeled as planned. This is a local MVP using sample records, not a deployment of the client's production agents.

## Requirements and implementation

| Requirement | Implemented behavior | Verification |
| --- | --- | --- |
| Agent catalog and metadata intake | Ten sample listings; canonical and simple intake shapes; validated links, IDs, ACL and publication metadata | Metadata, normalization, validation and ACL API tests |
| Discovery and NLP search | Six configurable carousels; five role-derived personas; domain filters; optional Claude interpretation with local fallback and match explanations | Ranking API tests; browser search |
| Agent details and actions | Overview, owner, access instructions, documentation, architecture and related learning. Local pending access requests. Enterprise launch, access portal and owner contact use configured destinations; sample destinations are labeled | Detail/resource/API tests; browser request and history |
| Useful feedback | Search and detail feedback saved per user; failures stay visible and can be retried | API isolation test; frontend failed-save test |
| Authorized learning | Active, approved records with an allowed group; permissions enforced on catalog, search, paths, direct links, recommendations and progress | ACL and permission-revocation tests |
| Role-based learning | Six authored paths with ordered steps, next item, completion counts and prerequisites; required, continuing and recommended sections | Path, prerequisite and recommendation tests; browser walkthrough |
| Learning entry points | Catalog, role paths, getting started, best practices, product docs and quick references; search/type/status filters | Frontend routing and filtering test |
| Progress and coverage | Per-user state, monotonic percentages and statuses, one completion event per item. Topic coverage counts; no proficiency claim | Multiple-process write test; API and browser account-isolation checks |
| Shared hub state | SQLite users, hashed sessions, preferences, read notifications, events, feedback, access requests and learning progress | Session, SQL, migration and account tests |
| Working account controls | Demo role accounts in development; password accounts in production mode; sign-out revokes sessions; admin-only persona preview | Authentication and frontend session tests |

Recommendations use authored metadata and explicit role rules. Progress removes completed recommendations and determines the continuing section; it does not learn behavioral preferences. Collected footprints do not change ranking.

## Run locally

Requirements: Python 3.12, uv, and a Node version supported by the locked Vite package. Python is pinned in `backend/.python-version`.

In a terminal:

```powershell
cd backend
uv sync --frozen
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

In a second terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open [MUFG](http://localhost:5173). Choose a clearly labeled demo account. Sai is the sample hub administrator; the five other accounts demonstrate the role mappings and independent state. Taylor can see builder-restricted learning; Alex cannot.

The backend reads `backend/.env`. Copy `.env.example` if needed. Search works without an API key. To enable Claude, set `ANTHROPIC_API_KEY`, `CREDITWIZ_DISABLE_LLM=0` and a model available to the configured Anthropic account. Live Claude calls were not part of verification.

For another frontend port, add its exact origin to `CREDITWIZ_ORIGINS`. The frontend supports `CREDITWIZ_API_TARGET` to select a separate API during development.

## SQLite and existing data

All mutable state now lives in `backend/var/hub.db`, or in `CREDITWIZ_VAR_DIR/hub.db`. SQLite runs locally without a database server. Writes use transactions, including a single transaction for learning completion and its event. WAL supports concurrent local processes; the database belongs on a local disk.

On first connection, migration imports legacy `learning.db`, `learning_progress.json`, `interactions.jsonl` and `feedback.jsonl`. Existing SQL progress wins over the older JSON copy. Import is recorded once; original files remain untouched. Old footprints retain the original single-user prototype's identity and are tagged as legacy imports.

Back up the database using SQLite's backup API or stop the service before copying its database files. Keep runtime state out of Git. A new empty `CREDITWIZ_VAR_DIR` creates an independent demo without deleting an existing one.

Authored agents, learning, paths and persona rules remain in version-controlled JSON. Moving authored content into SQL is unnecessary for this MVP.

## Account setup beyond the demo

Development mode is deliberately passwordless and must remain local. For a hosted environment, provision accounts, set `CREDITWIZ_ENV=production`, use HTTPS and set the allowed frontend origin. Production disables demo account selection and requires password accounts; this is local authentication, not enterprise SSO.

```powershell
cd backend
uv run python -m app.manage user --email employee@example.com --name "Example Employee" --role "Business Analyst" --group AI-Hub-Users
```

The command prompts privately for a password (minimum 12 characters). Repeating it updates that account and revokes its sessions. Repeat `--group` for each granted directory group. `AI-Hub-Admins` permits persona preview; it does not bypass a content ACL. Profile role changes update the derived persona on the next request.

Optional first-administrator bootstrap variables are documented in `.env.example`. No passwords or raw session tokens are stored in the database. Sessions expire after eight hours. Hosted enterprise rollout still requires the organization's SSO, deployment and operating controls; those integrations are outside the accepted MVP.

## Publishing authored content

Validate metadata before starting a review:

```powershell
cd backend
uv run python -m app.manage validate
```

The validator checks models, duplicate IDs, safe links, unknown references, paths and prerequisite cycles. Enterprise records require explicit publication and audience metadata. Only active records with `review_status: "approved"` and a matching `audience_groups` entry are returned. Empty groups allow no users. Role/persona matching is relevance, separate from permission.

Learning paths define ordered `steps`. Items declare `prerequisites`; blocked content cannot be marked started or completed. If a prerequisite is unavailable to a user, its identifier is hidden and the item asks the user to contact the content owner. Owners, mappings and review dates in the supplied catalog are illustrative and require client approval.

Opening an accessible item records “started” with 0%. Native video progress uses playback position; an embedded YouTube player has no invented watch percentage. “Mark as complete” is explicit self-reporting. This does not certify watching, exam results or proficiency.

## Validation

```powershell
cd backend
uv run pytest -q
uv run python -m app.manage validate
```

```powershell
cd frontend
npm test
npm run lint
npm run build
```

Verified on 2026-09-08: 46 backend tests and 6 frontend tests pass; frontend lint and production build pass; catalog validation reports 10 agents, 22 learning items and 6 paths. The backend test runner emits one upstream Starlette/AnyIO deprecation warning.

Regression coverage includes independent users, unauthorized direct URLs, forged persona overrides, revoked permissions, expired sessions, CSRF/origin checks, rate limits, prerequisite enforcement, concurrent completion updates, migration, failed feedback and canceled searches. Browser checks use a separate temporary database.

## Client inputs still required for enterprise use

- Confirmed agent listings, owners, launch/access destinations, categories and persona labels.
- Approved source materials, audience groups, path ordering and content owners.
- Enterprise authentication, LMS/Workday/Confluence/registry connectors and deployment configuration.
- An agreed proficiency measure, if proficiency is later added.

These are explicitly deferred integrations or client content decisions. The MVP does not invent them, send access requests externally, or implement the other seven pillar workflows.
