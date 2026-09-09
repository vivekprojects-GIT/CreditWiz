# Screening agent pattern

Screens entities against external lists, resolves likely false positives with evidence and produces an auditable disposition.

## How it works

```text
Entity submitted (name, identifiers, country)
    ↓
Screening API calls across sanctions, PEP and media sources
    ↓
Entity resolution: model compares hit attributes with the customer record
    ↓
Explanation: why each hit is a likely match or false positive
    ↓
Preliminary risk rating and EDD questions
    ↓
Analyst disposition recorded to the audit trail
```

## Design principles

- The agent never clears a true hit; it only explains and ranks.
- Every decision writes evidence to the case before returning.
- List refresh cadence is displayed with each result.

## Used by

- Sanctions Review Agent

## Reference implementation

Ask the Developer Platform team for the starter repository for this pattern. It includes the pipeline, evaluation harness and the standard observability hooks.
