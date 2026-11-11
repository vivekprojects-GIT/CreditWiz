# Data model

Nexus keeps its data in two places:

- **Catalogue content** in JSON files under `backend/data/`. Read-only at run time: agents, learning, "Your work", community, prompts and the list of source systems.
- **What people do** in SQLite at `backend/var/hub.db` (`backend/app/database.py`): sign-ins, progress, ratings, feedback, requests and Super Agent conversations.

The two are joined only by ids. SQLite stores `item_id`, `agent_id`, `prompt_id` and `post_id` as plain text that names a record in a JSON file. Nothing enforces those links.

The diagrams show every field. How to read them:

- `string[]` is a list of values held on the record itself.
- An entity drawn with no fields is defined in another diagram.
- Entities marked *(embedded)* below are objects stored inside their parent record, not records of their own.
- `CAPABILITY`, `BUSINESS_DOMAIN` and `TOPIC` are shared words, not files: the same strings appear on agents, learning items and personas, and matching on them is how the three are related.

## 1. Agents and discovery (JSON)

```mermaid
erDiagram
  AGENT ||--|| AGENT_OWNER : "owned by"
  AGENT ||--|| AGENT_ACCESS : "reached through"
  AGENT ||--o{ AGENT_DOCUMENT : "documents"
  AGENT_DOCUMENT }o--|| DOCUMENT_TYPE : "is a"
  AGENT_DOCUMENT }o--o| SOURCE_SYSTEM : "lives in"
  DOCUMENT_TYPE }o--o{ SOURCE_SYSTEM : "lives in"
  LINK_GROUP }o--o{ SOURCE_SYSTEM : "groups"
  AGENT }o--o{ CAPABILITY : "has"
  AGENT }o--o{ BUSINESS_DOMAIN : "works in"
  AGENT }o--o{ PERSONA : "built for"
  PERSONA ||--|| PERSONA_INTERESTS : "interests"
  PERSONA_INTERESTS }o--o{ CAPABILITY : "wants"
  PERSONA_INTERESTS }o--o{ BUSINESS_DOMAIN : "wants"
  CAROUSEL ||--|| CAROUSEL_RULE : "rule"
  CAROUSEL }o--o{ AGENT : "selects by rule"
  AGENT {
    string id PK
    string name
    string tagline
    string version
    string description
    string problem_solved
    string[] business_domains
    string[] use_cases
    string[] personas "persona ids"
    string[] capabilities
    string[] services
    string[] example_tasks
    string[] tags
    string category
    string platform
    string[] tools_services
    string[] models
    string architecture_pattern
    string status "production, pilot, beta, in_development, deprecated"
    string documentation_url
    string architecture_url
    string created_at
    string updated_at
    bool featured
    int popularity
    string[] audience_groups "directory groups that may see it"
    bool active
    string review_status "draft, approved, retired"
    string source_kind "sample, enterprise"
  }
  AGENT_OWNER {
    string team
    string name
    string email
  }
  AGENT_ACCESS {
    string type "open, request, restricted"
    string how
    string launch_url
    string request_url
  }
  AGENT_DOCUMENT {
    string type FK "document type id"
    string system FK "source system id"
    string url
    string description
  }
  DOCUMENT_TYPE {
    string id PK
    string abbreviation
    string name
    string about
    string feeds
    string[] lives_in "source system ids"
    string owner
  }
  SOURCE_SYSTEM {
    string id PK
    string name
    string kind
    string feeds
    string owner
    string location
    string connection
  }
  LINK_GROUP {
    string id PK
    string name
    string[] systems "source system ids"
  }
  PERSONA {
    string id PK
    string label
    string description
  }
  PERSONA_INTERESTS {
    string[] domains
    string[] capabilities
    string[] tags
  }
  CAROUSEL {
    string id PK
    string title
    string subtitle
  }
  CAROUSEL_RULE {
    string type "persona, category, featured, recent"
    string value
  }
  CAPABILITY {
    string name
  }
  BUSINESS_DOMAIN {
    string name
  }
```

| Entity | File |
| --- | --- |
| Agent, with its owner, access and documents *(embedded)* | `agents.json` |
| Persona, with its interests *(embedded)* | `personas.json` |
| Carousel, with its rule *(embedded)* | `carousels.json` |
| Source system, document type, link group | `knowledge-sources.json` (`systems`, `document_types`, `link_groups`) |

Notes:

- A source system is an MUFG system where an agent's documents and records live: Confluence, SharePoint, JIRA, ServiceNow. It is a reference list, not a knowledge base or a search index. Nexus links to documents where they live and keeps no copies. The file is still named `knowledge-sources.json`.
- A carousel holds a rule, not a list. Which agents appear is worked out from the rule on each request.
- `services`, `example_tasks` and `documents` are part of the agent model but no sample agent fills them yet.
- A user is given a persona from their job title and department by `persona-mapping.json`. That mapping is rules, not a stored link.

## 2. Learning and "Your work" (JSON)

```mermaid
erDiagram
  LEARNING_PATH ||--o{ LEARNING_ITEM : "steps"
  LEARNING_ITEM ||--o{ LESSON : "lessons"
  LEARNING_ITEM }o--o{ LEARNING_ITEM : "prerequisite"
  LEARNING_ITEM }o--o{ AGENT : "related agent"
  LEARNING_ITEM }o--o{ PERSONA : "mapped to"
  LEARNING_ITEM }o--o{ PERSONA : "required for"
  LEARNING_ITEM }o--o{ CAPABILITY : "teaches"
  LEARNING_ITEM }o--o{ TOPIC : "covers"
  PERSONA }o--o{ LEARNING_PATH : "role paths"
  PERSONA ||--o{ JOURNEY : "has jobs"
  JOURNEY ||--o{ JOURNEY_STEP : "steps"
  JOURNEY ||--o{ JOURNEY_SYSTEM : "systems used"
  JOURNEY ||--o{ JOURNEY_LINK : "what helps"
  JOURNEY_LINK }o--o| AGENT : "ref agent"
  JOURNEY_LINK }o--o| LEARNING_ITEM : "ref learning"
  JOURNEY_LINK }o--o| ASSET : "ref asset"
  ASSET ||--|| ASSET_TRUST : "trust"
  LEARNING_ITEM {
    string id PK
    string title
    string type "video, course, confluence, guide, documentation, quick-reference, best-practice"
    string description
    string body
    string[] topics
    string[] capabilities
    string[] personas "persona ids"
    string[] required_for "persona ids"
    string path FK "learning path id"
    string[] prerequisites "learning item ids"
    string[] related_agents "agent ids"
    string level
    int duration_seconds
    string[] tags
    string[] outcomes
    string url
    string youtube_id
    string poster_url
    string source "the provider"
    string provider_ref "the provider's own id"
    string instructor
    bool licensed
    string owner
    string[] audience_groups "directory groups that may see it"
    bool active
    string review_status
    string reviewed_at
    string source_kind "sample, enterprise"
  }
  LESSON {
    string title
    int minutes
    string kind
  }
  LEARNING_PATH {
    string id PK
    string title
    string blurb
    string[] steps "learning item ids, in order"
    string owner
    string version
  }
  JOURNEY {
    string id PK
    string persona FK
    string title
    string summary
    string objective
    string[] needs
    string[] keywords
  }
  JOURNEY_STEP {
    string title
    string detail
  }
  JOURNEY_SYSTEM {
    string system
    string does
  }
  JOURNEY_LINK {
    string ref FK "agent, learning or asset id"
    string intent "find, learn, improve, ask, contribute"
    string why
  }
  ASSET {
    string id PK
    string kind
    string title
    string summary
    string provided_by
    string action_label
    string action_url
    string source_kind
  }
  ASSET_TRUST {
    string purpose
    string owner_team
    string who_can_use
    string how_to_access
    string[] guardrails
    string feedback
  }
  TOPIC {
    string name
  }
```

| Entity | File |
| --- | --- |
| Learning item, with its lessons *(embedded)* | `learning.json` (`items`) |
| Learning path | `learning.json` (`paths`) |
| Persona to learning paths | `learning.json` (`persona_paths`) |
| Journey, with its steps, systems and links *(embedded)* | `journeys.json`, grouped by persona |
| Asset, with its trust details *(embedded)* | `assets.json` |

Notes:

- A journey link holds one reference. Its prefix says what it points at: `agent:`, `learning:` or `asset:`.
- A learning item belongs to one path (`path`), and a path lists its items in order (`steps`).

## 3. Community and prompts (JSON)

```mermaid
erDiagram
  COMMUNITY ||--o{ POST : "contains"
  PERSON ||--o{ POST : "writes"
  POST ||--o{ POST_REPLY : "replies"
  PERSON ||--o{ POST_REPLY : "writes"
  PERSON ||--o| EXPERT : "is"
  EXPERT }o--o{ COMMUNITY : "active in"
  COMMUNITY }o--o{ PERSONA : "relevant to"
  COMMUNITY }o--o{ TOPIC : "about"
  POST }o--o{ TOPIC : "about"
  DESK ||--o{ PROMPT : "owns"
  PROMPT ||--|| PROMPT_CONTRIBUTOR : "written by"
  PROMPT ||--o| PROMPT_TUTORIAL : "tutorial"
  PROMPT ||--o{ PROMPT_INPUT : "inputs"
  PROMPT ||--o{ PROMPT_REVIEW : "reviews"
  PROMPT ||--o{ PROMPT_COLLABORATOR : "collaborators"
  COMMUNITY {
    string id PK
    string name
    string description
    string privacy
    int member_count
    string[] topics
    string[] personas "persona ids"
  }
  POST {
    string id PK
    string community_id FK
    string author FK "person id"
    string created_at
    string kind
    string title
    string body
    string[] topics
    int likes
  }
  POST_REPLY {
    string id PK
    string author FK "person id"
    string created_at
    string body
    int likes
  }
  PERSON {
    string id PK
    string name
    string title
  }
  EXPERT {
    string person FK
    string[] topics
    string[] community_ids
  }
  DESK {
    string id PK
    string label
    string plural
    string[] job_titles
    string department
    json teams
  }
  PROMPT {
    string id PK
    string desk FK
    string category
    string scope
    string title
    string description
    string narrative
    string body
    string sample_output
    string[] tags
    string[] guidelines
    int views
    int uses
    float rating
    int ratings
    int hours_saved
    string repetition
    string created
    string updated
    bool validated
    string risk "Low, Medium, High"
    string risk_note
    string source_kind
  }
  PROMPT_CONTRIBUTOR {
    string name
    string initials
    string team
  }
  PROMPT_TUTORIAL {
    string title
    string duration
    string views
  }
  PROMPT_INPUT {
    string label
    string type
    string note
    bool required
  }
  PROMPT_REVIEW {
    string name
    string initials
    string team
    int stars
    string when
    string comment
  }
  PROMPT_COLLABORATOR {
    string name
    string initials
    string role
  }
  PROMPT_TEMPLATE {
    string id PK
    string name
    string use
    string when
    string body
  }
```

| Entity | File |
| --- | --- |
| Community, person, expert | `community.json` |
| Post, with its replies *(embedded)* | `community.json` (`posts`) |
| Prompt, with its contributor, tutorial, inputs, reviews and collaborators *(embedded)* | `prompts.json` (`prompts`) |
| Desk, prompt template | `prompts.json` (`desks`, `templates`) |

## 4. User activity (SQLite)

Every table but the last two belongs to a user.

```mermaid
erDiagram
  USERS ||--o{ SESSIONS : "signs in"
  USERS ||--o| PREFERENCES : "has"
  USERS ||--o{ NOTIFICATION_READS : "reads"
  USERS ||--o{ LEARNING_PROGRESS : "tracks"
  USERS ||--o{ LEARNING_RATINGS : "rates"
  USERS ||--o{ EVENTS : "generates"
  USERS ||--o{ FEEDBACK : "gives"
  USERS ||--o{ ACCESS_REQUESTS : "requests"
  USERS ||--o{ SAVED_PROMPTS : "saves"
  USERS ||--o{ CONTRIBUTIONS : "submits"
  USERS ||--o{ HUB_SESSIONS : "asks"
  USERS ||--o{ COMMUNITY_REPLIES : "replies"
  USERS ||--o{ COMMUNITY_LIKES : "likes"
  USERS {
    text id PK
    text email UK
    text password_hash
    text profile "directory profile, JSON"
    int active
  }
  SESSIONS {
    text token_hash PK
    text user_id FK
    real expires_at
  }
  PREFERENCES {
    text user_id PK, FK
    text value "JSON"
  }
  NOTIFICATION_READS {
    text user_id PK, FK
    text notification_id PK
  }
  LEARNING_PROGRESS {
    text user_id PK
    text item_id PK "learning item id"
    text status "not_started, in_progress, completed"
    int progress "0 to 100"
    text started_at
    text completed_at
    text updated_at
  }
  LEARNING_RATINGS {
    text user_id PK, FK
    text item_id PK "learning item id"
    int stars "1 to 5"
    text created_at
    text updated_at
  }
  EVENTS {
    text id PK
    text user_id
    text at
    text payload "JSON"
    text event_key UK
  }
  FEEDBACK {
    text id PK
    text user_id
    text at
    text payload "JSON"
  }
  ACCESS_REQUESTS {
    text id PK
    text user_id FK
    text agent_id "agent id"
    text reason
    text status "pending by default"
    text created_at
  }
  SAVED_PROMPTS {
    text user_id PK, FK
    text prompt_id PK "prompt id"
    text saved_at
  }
  CONTRIBUTIONS {
    text id PK
    text user_id FK
    text kind "prompt, video, agent"
    text status "in_review, live, returned"
    text title
    text payload "JSON"
    text created_at
    text desk
    text department
    text audience "team, department, everyone"
  }
  HUB_SESSIONS {
    text id PK
    text session_id
    text user_id FK
    text intents "JSON list"
    text activity
    text selected_pillars "JSON list"
    text recommended_asset_ids "JSON list"
    text selected_asset_ids "JSON list"
    text feedback "helpful, not_helpful"
    text sensitivity
    text plan_source
    text reply_source
    int latency_ms
    text created_at
  }
  COMMUNITY_REPLIES {
    text id PK
    text thread_id "post id"
    text user_id FK
    text body
    text created_at
  }
  COMMUNITY_LIKES {
    text user_id PK, FK
    text post_id PK "post id"
    text created_at
  }
  LOGIN_ATTEMPTS {
    text address PK
    int failures
    real until_at
  }
  MIGRATIONS {
    text name PK
  }
```

Where a table points into the catalogue:

| Table | Column | Names a record in |
| --- | --- | --- |
| `learning_progress`, `learning_ratings` | `item_id` | `learning.json` items |
| `access_requests` | `agent_id` | `agents.json` |
| `saved_prompts` | `prompt_id` | `prompts.json` |
| `community_replies` | `thread_id` | `community.json` posts |
| `community_likes` | `post_id` | `community.json` posts |
| `hub_sessions` | `recommended_asset_ids`, `selected_asset_ids` | agents, learning items and assets |

Notes:

- `hub_sessions` holds one row per question the Super Agent answered: ids and measures only, never the question text.
- `events` and `feedback` keep their detail as JSON in `payload`.
- `users.profile` is the directory profile as JSON. The persona is not stored: it is worked out from the job title and department with `persona-mapping.json`.
- One request per user per agent: `access_requests` is unique on `user_id` and `agent_id`.

## Not drawn

- `policy.json`: what the model may be sent, by data sensitivity. One record.
- `user.json`: the mocked directory profile for the prototype. One record.
- `persona-mapping.json`: the rules that give a user a persona.
- `agent-metadata-template.json`: the template for registering an agent.
