# Workflow agent pattern

Drives a multi-step business process, calling systems and drafting outputs, with a human approving every external action.

## How it works

```text
Trigger: case created or user request
    ↓
State loaded from the system of record
    ↓
Agent decides the next step from the process definition
    ↓
Tools called: read case data, check rules, draft outputs
    ↓
Draft presented for human approval
    ↓
Approved action executed and state updated
```

## Design principles

- Process definition lives in configuration, not in the prompt.
- External side effects (send, submit) always require approval.
- Every step is idempotent so a retry never duplicates work.

## Used by

- Customer Onboarding Assistant
- Dispute Resolution Agent
- Collections Outreach Agent

## Reference implementation

Ask the Developer Platform team for the starter repository for this pattern. It includes the pipeline, evaluation harness and the standard observability hooks.
