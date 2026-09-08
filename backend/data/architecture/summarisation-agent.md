# Summarisation agent pattern

Turns a large, mixed set of case records into a structured brief with a recommended next step.

## How it works

```text
Case selected
    ↓
Retrieval gathers alerts, transactions, notes and signals
    ↓
Model produces a structured brief against a fixed template
    ↓
Claims in the brief are linked back to the source records
    ↓
Follow-up questions answered from the same context
```

## Design principles

- Fixed output template keeps briefs comparable across cases.
- Every statement is traceable to a source record.
- No new data is fetched during summarisation; it works on what is in the case.

## Used by

- Fraud Case Summariser

## Reference implementation

Ask the Developer Platform team for the starter repository for this pattern. It includes the pipeline, evaluation harness and the standard observability hooks.
