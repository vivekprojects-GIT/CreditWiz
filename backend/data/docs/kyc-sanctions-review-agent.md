## Overview

Runs sanctions screening for a KYC review against the OFAC, EU, UN and OFSI lists, and presents what it found for a reviewer to disposition.

> [!WARNING] No hit is cleared by the agent
> The agent presents what it found. A reviewer dispositions every hit.

## Getting started

1. Open to all employees. Sign in with your MUFG account.
2. Find the Sanctions Review Agent in the AI Marketplace under **KYC Workflow**.
3. Start with one of the requests below, then adapt it to your case.

## What to give it and what you get back

**Input.** The client and the related parties on the case.

**Output.** Screening results against the OFAC, EU, UN and OFSI lists, with each potential match presented for a reviewer.

## What you can ask

- Screen a client against OFAC, EU, UN and OFSI lists
- Review sanctions hits raised during a KYC case
- Evidence sanctions screening for an audit trail

## Capabilities

- **Sanctions screening**
- **Entity resolution**
- **Audit trail**
- **Cited source annotation**

## Where it fits in the workflow

The KYC Supervisor Agent delegates the sanctions stage to it and aggregates the result into the case view. It screens against the OFAC, EU, UN and OFSI lists. The KYC Completeness Agent checks that this stage has reported OK before the case is closed.

## Platform, tools and models

> [!NOTE] To be confirmed
> The platform, tools and models behind this agent will be listed here once the KYC Programme confirms them.

## Limitations and guardrails

- It never clears a hit. A reviewer dispositions every potential match.
- Screening covers the OFAC, EU, UN and OFSI lists.
- This agent is in development. Check its output before relying on it.

## Frequently asked questions

**Which lists does it screen against?**

OFAC, EU, UN and OFSI.

**Can the screening be evidenced for audit?**

Yes. Screening is recorded so that it can be evidenced for an audit trail.

## Support

The **KYC Programme** owns this agent. Named contacts will appear here once the owning team confirms the listing.
