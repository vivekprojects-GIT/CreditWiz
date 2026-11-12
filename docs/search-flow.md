# Agent search: query flow

```
User Query  →  Embedding  →  Hybrid Search  →  Context
```

One request through `POST /api/marketplace/search`, exactly as the code runs it.
No model reads the request at any stage: the query is embedded as typed, so what
you search for is what you asked for, and the same words return the same agents
in the same order every time. The order is closest in meaning first: semantic
similarity, with no fusion step and no reranker. Permission is
applied before anything is scored and enforced again after. The numbers are the
live constants.

```mermaid
flowchart TB
  Q["User query<br/>typed as-is, nothing added"]
  G["Identity + access<br/>session · request header · origin allowlist"]
  V["Authorized agents<br/>active · approved · your groups"]
  E["Embedding<br/>ONNX MiniLM-L6 · 384 numbers · ~55 ms"]
  R["Order by similarity<br/>closest in meaning first, keyword-only hits after"]
  T{"Relevance gate<br/>0.30 absolute and 65% of best<br/>or 50% of the best keyword score"}
  N["No match<br/>with next steps"]
  C["Cut to 6<br/>and drop anything outside your groups, again"]
  J[("agents.json<br/>owner · status · access · platform · dates")]
  X["Context<br/>why this matched · coverage % · trace"]
  A["Results<br/>closest in meaning first"]

  subgraph H ["Hybrid search"]
    direction LR
    K["BM25<br/>exact names, acronyms, IDs<br/>top 6"]
    S["Semantic<br/>ChromaDB cosine, audience filter inside the query<br/>top 6"]
  end

  Q --> G
  G --> V
  V --> E
  E --> S
  E --> K
  S -- "ids to similarity" --> R
  K -- "ids to BM25 score" --> R
  R --> T
  T -- "nothing clears the floors" --> N
  T -- "survivors, in similarity order" --> C
  C -- "ids only" --> J
  J -- "full records" --> X
  X --> A
  V -. "enforced again after ordering" .-> C

  classDef src fill:#f4f4f2,stroke:#141516,stroke-width:1.5px,color:#141516
  class J src
```

## What each stage does, and what it falls back to

| Stage | Behaviour | If it fails |
| --- | --- | --- |
| Identity + access | Custom header required; Origin must be on the allowlist, the Render URL, or any loopback port outside production. | `403` naming the reason; `401` without a session. |
| Authorized agents | Computed before any scoring, and pushed into retrieval: the vector query carries a `$contains` filter on the agent's audience, and BM25 scores only permitted ids. | Nothing impermissible is retrieved at all, and the drop after ordering still runs as a second enforcement. |
| Embedding | The query as typed. Agents were embedded once at startup, keyed by a content fingerprint, so a restart re-embeds nothing. | Index broken or empty → keyword-only. |
| Hybrid search | Two rankers over the same agent text. Semantic finds meaning, BM25 finds `W-8`, `OFSI`, `AHR` and exact names — measured, semantic alone misses those three entirely. | Either side can return nothing; the other still answers. |
| Order | Semantic similarity, highest first. An agent only BM25 found (an exact name or acronym the embedding missed) has no similarity and follows, by its keyword score. The two scores are never added or fused. | — |
| Relevance gate | A retriever always returns something, so the gate decides what is shown. Floors are set for a bare query: a short question scores far lower than an expanded one for the same meaning. | No match, with next steps. |
| Context | Retrieval returns ids and numbers only. Every field on screen — owner, status, access, dates — is read from `agents.json` after the id comes back. | — |

## Three properties to state in the review

- **Permission first, and again after.** The visible set is computed before scoring and filters inside the vector query; the dotted edge is the second enforcement. A retrieval fault cannot surface an agent someone may not see.
- **No model in the search path.** Nothing stands between what was typed and what was searched, and nothing reorders the results afterwards. The same query always returns the same agents in the same order.
- **`agents.json` is the record of truth; the index is derived.** Delete the index directory and you lose a rebuild, nothing else. Owner and access can never be stale, because they are read fresh from the catalogue every request.

Constants: candidates 6 per ranker · floors 0.30 / 65% / 50% · limit 6 · retrieval cache 256 · index ONNX MiniLM-L6-v2.

Latency: about **66 ms** end to end, measured before the reranker was removed on searches that skipped it. The 1.9–3.5 s the rerank added is gone.
