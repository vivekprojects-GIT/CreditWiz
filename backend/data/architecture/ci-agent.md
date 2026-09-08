# CI agent pattern

Runs inside the delivery pipeline on every change, producing findings that engineers act on before merge.

## How it works

```text
Pull request opened or updated
    ↓
Pipeline job checks out the diff and context
    ↓
Static analysis and model review run in parallel
    ↓
Findings merged, de-duplicated and ranked by severity
    ↓
Comments posted to the pull request
    ↓
Engineer resolves or dismisses; branch protection decides the merge
```

## Design principles

- Advisory by default; blocking rules are opt-in per repository.
- Runs on the diff plus minimal context to keep cost and latency low.
- Findings carry a rule ID so teams can tune or suppress them.

## Used by

- Code Review Assistant

## Reference implementation

Ask the Developer Platform team for the starter repository for this pattern. It includes the pipeline, evaluation harness and the standard observability hooks.
