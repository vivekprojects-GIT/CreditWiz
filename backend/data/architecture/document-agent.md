# Document agent pattern

Reads documents, extracts structured fields, checks them against a source of truth and reports gaps.

## How it works

```text
User or workflow submits documents
    ↓
Ingestion: virus scan, format normalisation, OCR when needed
    ↓
Extraction: model reads each page into a typed schema
    ↓
Validation: fields checked against the application record and business rules
    ↓
Report: completeness and consistency findings with evidence
    ↓
Human review and sign-off
```

## Design principles

- Keep documents in the vault; pass references, not copies.
- Every extracted field carries a confidence score; low confidence is surfaced, never hidden.
- The report, not the raw model output, is the contract with downstream systems.

## Used by

- CIP Agent
- Contract Analyzer

## Reference implementation

Ask the Developer Platform team for the starter repository for this pattern. It includes the pipeline, evaluation harness and the standard observability hooks.
