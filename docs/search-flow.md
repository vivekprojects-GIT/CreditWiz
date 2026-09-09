# Agent search: query flow

One request through `POST /api/marketplace/search`, exactly as the code runs it.
Permission is applied before anything is scored; the language model only
restates the question; two retrievers are fused by rank; everything after
fusion removes results and never reorders them. The numbers are the live
constants. A published page version of this diagram is kept alongside the
review materials.

```mermaid
flowchart TB
  Q(["Typed request<br/>“check customers against sanctions lists”"])
  G["Session boundary<br/>X-CreditWiz-Request header · Origin allowlist · session cookie"]
  V["Visible catalogue<br/>active · approved · your groups ∩ audience_groups"]
  U{"Understand<br/>ANTHROPIC_API_KEY set?"}
  C["Claude claude-sonnet-5<br/>structured SearchIntent · 20 s timeout · cached 256<br/>domains and capabilities filtered to the catalogue"]
  L["Local lexicon<br/>same SearchIntent shape"]
  E["Enriched text<br/>query + summary + domains + capabilities"]
  S["Semantic · ChromaDB<br/>embed once, ONNX MiniLM, 1 thread<br/>top 12 by cosine · result cache 256"]
  K["Keyword · BM25<br/>same agent text · exact names, acronyms, IDs<br/>top 12"]
  R["Reciprocal Rank Fusion<br/>score = Σ 1 / (60 + rank)"]
  T{"Relevance gate<br/>sim ≥ 0.45 and ≥ 65% of best<br/>or keyword ≥ 50% of best keyword"}
  N(["No match<br/>“zebra origami” scores 0.00 everywhere"])
  D["Cut, never reorder<br/>drop anything not in the visible set · ?domain= filter · limit 6"]
  X["Explain from metadata<br/>why: capabilities and domains the request asked for<br/>coverage % on the best match only"]
  F["Footprint<br/>engine · intent · both candidate lists · scores · embed_ms<br/>recorded, never ranked on"]
  A(["Response<br/>Best match · 2nd match · 3rd match"])

  Q --> G
  G -- "403 / 401 on failure" --> G
  G --> V
  V --> U
  U -- "yes" --> C
  U -- "no, or timeout" --> L
  C --> E
  L --> E
  E -- "one embedding" --> S
  E -- "query + domains + capabilities" --> K
  S -- "ids → similarity" --> R
  K -- "ids → BM25 score" --> R
  R --> T
  T -- "nothing clears it" --> N
  T -- "survivors, in fused order" --> D
  D --> X
  X --> F
  F --> A
  V -. "an agent you may not see can be retrieved,<br/>and is dropped here by construction" .-> D

  classDef fuse fill:#fdecec,stroke:#e60000,stroke-width:1.5px,color:#141516
  class R fuse
```

## What each stage does, and what it falls back to

| Stage | Behaviour | If it fails |
| --- | --- | --- |
| Session boundary | Custom header required; Origin must be on the allowlist, the Render URL, or any loopback port outside production. | `403` naming the reason; `401` without a session. |
| Visible catalogue | Filtered per user before any scoring. Both indexes are built from the whole catalogue and shared. | An invisible agent can be retrieved; it is dropped before display and can never surface. |
| Understand | Claude returns a restatement plus domains and capabilities, intersected with the real catalogue so it cannot invent a category. It never picks an agent. | Local lexicon produces the same shape. Any Claude failure lands here. |
| Semantic retrieval | Agents embedded once at start, keyed by a content fingerprint; only the query is embedded per search. About 0.5 s on Render's free tier. | Index broken or empty → keyword-only. |
| Keyword retrieval | BM25 over the same text the semantic index embeds, so a ranking difference is a difference in method, not input. | Rebuilt in microseconds from the catalogue. |
| Fusion | Ranks, not scores: a cosine in 0–1 and a BM25 in 0–10 never meet as magnitudes. `k = 60`. | — |
| Relevance gate | RRF always returns something, so the gate decides what is shown. Calibrated on this catalogue: real matches 0.54–0.85, noise 0.35–0.47. Retune when the model or the catalogue changes. | No match, with next steps. |
| Explain | "Why this matched" names the agent's own metadata the request asked for. Not generated prose. | Percentage omitted rather than invented. |
| Footprint | Enough to reconstruct the ranking afterwards. Readable at `GET /api/context/events`, scoped to the user. | A test asserts ranking is identical before and after a user acts. |

## Three properties to state in the review

- **Permission first, never after.** The visible set is computed at step three. Scoring only ever sees agents the person may use; the dotted edge is the guarantee.
- **The model understands; the registry decides.** Claude produces a `SearchIntent` and nothing else. Owner, status, access and URLs come from `agents.json` alone.
- **Every step degrades.** No key → lexicon. Timeout → lexicon. Broken index → keyword only. Nonsense → no match. The demo has no single point of failure.

Constants: candidates 12 · k 60 · floors 0.45 / 65% / 50% · limit 6 · intent cache 256 · retrieval cache 256 · model `claude-sonnet-5` · index ONNX MiniLM-L6-v2.
