## Overview

Orchestrates the KYC review end to end. It delegates each stage to the specialist agent that owns it, tracks which stages are outstanding, and aggregates the specialists' results into a single case view for the reviewer.

> [!INFO] The centre of the KYC workflow
> Every other KYC agent either sends work to the supervisor or receives work from it. The architecture page shows how the stages connect.

## Getting started

1. Open to all employees. Sign in with your MUFG account.
2. Find the KYC Supervisor Agent in the AI Marketplace under **KYC Workflow**.
3. Start with one of the requests below, then adapt it to your case.

## What to give it and what you get back

**Input.** A KYC case, with the documents the client has provided so far.

**Output.** One case view: the result of each review stage, the stages still outstanding, and the gaps that need a follow-up with the client.

## What you can ask

- Run a KYC case through the review workflow
- Delegate a review stage to the specialist agent that owns it
- Aggregate specialist results into one case view
- See which stages of a case are still outstanding

## Capabilities

- **Workflow orchestration**
- **Case summarisation**
- **Audit trail**
- **Cited source annotation**

## Where it fits in the workflow

The Client Response Analyzer Agent routes each incoming document to the case the supervisor is running. The supervisor delegates every review stage to its specialist: CIP, Tax, Ownership and Org Chart, FinCEN BO Form, Sanctions Review and Adverse Media. When a stage finds a gap, it asks the Email Drafting Agent for a follow-up. When every stage is done, the KYC Completeness Agent closes the case.

## Platform, tools and models

> [!NOTE] To be confirmed
> The platform, tools and models behind this agent will be listed here once the KYC Programme confirms them.

## Limitations and guardrails

- The supervisor delegates and aggregates. It does not review documents itself.
- A case closes only after the KYC Completeness Agent confirms that every stage has reported OK.
- This agent is in development. Check its output before relying on it.

## Frequently asked questions

**Does it make the KYC decision?**

No. It prepares one case view so that a KYC analyst can decide.

**What happens when a document is missing?**

The stage that needs it reports a gap, and the supervisor asks the Email Drafting Agent to draft a request for the client.

## Support

The **KYC Programme** owns this agent. Named contacts will appear here once the owning team confirms the listing.
