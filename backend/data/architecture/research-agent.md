# Research agent pattern

Plans and runs multi-step searches across approved sources, then assembles a sourced evidence pack.

## How it works

```text
Target submitted (account or entity)
    ↓
Planner decides which sources to query and in what order
    ↓
Connectors query internal and approved external sources
    ↓
Findings de-duplicated and scored for confidence
    ↓
Evidence pack assembled with source and date per item
    ↓
Reviewer accepts or rejects items
```

## Design principles

- Only approved connectors; each one is allow-listed and logged.
- Nothing leaves the evidence pack without a source.
- Long-running: results stream in as connectors complete.

## Used by

- Asset Locator

## Reference implementation

Ask the Developer Platform team for the starter repository for this pattern. It includes the pipeline, evaluation harness and the standard observability hooks.
