## Overview

The final gate in the workflow. It validates that every specialist agent has reported OK for its stage, and populates Konect once the case is complete.

> [!SUCCESS] Closes the case
> A KYC case is complete only when this agent confirms every stage. Konect is populated last.

## Getting started

1. Open to all employees. Sign in with your MUFG account.
2. Find the KYC Completeness Agent in the AI Marketplace under **KYC Workflow**.
3. Start with one of the requests below, then adapt it to your case.

## What to give it and what you get back

**Input.** A KYC case with the results of each review stage.

**Output.** Confirmation that every stage has reported OK, or the stage that is still blocking the case. When the case is complete, it is populated in Konect.

## What you can ask

- Confirm every KYC stage has reported OK
- Populate Konect once a case is complete
- Identify which stage is blocking a KYC case

## Capabilities

- **Completeness checking**
- **Workflow orchestration**
- **Audit trail**
- **Cited source annotation**

## Where it fits in the workflow

It runs last. The KYC Supervisor Agent hands it the case once the specialists have reported. It checks each stage and, when everything is OK, populates Konect.

## Platform, tools and models

> [!NOTE] To be confirmed
> The platform, tools and models behind this agent will be listed here once the KYC Programme confirms them.

## Limitations and guardrails

- It does not re-run any review. It confirms that each specialist has reported OK.
- Konect is populated only when every stage is complete.
- This agent is in development. Check its output before relying on it.

## Frequently asked questions

**How do I find what is holding a case up?**

Ask it which stage is blocking the case. It names the stage that has not reported OK.

**When is Konect updated?**

Only once every stage of the case has reported OK.

## Support

The **KYC Programme** owns this agent. Named contacts will appear here once the owning team confirms the listing.
