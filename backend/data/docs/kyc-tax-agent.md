## Overview

Reviews the tax side of a KYC file. It checks W-8 and W-9 forms, establishes FATCA and CRS classification, and assesses treaty eligibility for the client.

> [!INFO] One of the review specialists
> The KYC Supervisor Agent delegates the tax stage to this agent and brings its result into the case view.

## Getting started

1. Open to all employees. Sign in with your MUFG account.
2. Find the Tax Agent in the AI Marketplace under **KYC Workflow**.
3. Start with one of the requests below, then adapt it to your case.

## What to give it and what you get back

**Input.** The client's W-8 or W-9 form and the supporting tax documents on the case.

**Output.** Whether the form is complete, the FATCA and CRS classification, and the treaty eligibility assessment.

## What you can ask

- Review a W-8 or W-9 form for completeness
- Establish FATCA and CRS classification for a client
- Assess treaty eligibility

## Capabilities

- **Tax classification**
- **Document extraction**
- **Completeness checking**
- **Cited source annotation**

## Where it fits in the workflow

The KYC Supervisor Agent delegates the tax stage to it and aggregates the result into the case view. The KYC Completeness Agent checks that this stage has reported OK before the case is closed.

## Platform, tools and models

> [!NOTE] To be confirmed
> The platform, tools and models behind this agent will be listed here once the KYC Programme confirms them.

## Limitations and guardrails

- It prepares the classification from the forms provided. A reviewer confirms it.
- It is not tax advice to the client.
- This agent is in development. Check its output before relying on it.

## Frequently asked questions

**Which forms does it review?**

W-8 and W-9 forms, together with the FATCA and CRS classification they support.

**Does it decide treaty eligibility?**

It assesses eligibility from the documents. A reviewer makes the decision.

## Support

The **KYC Programme** owns this agent. Named contacts will appear here once the owning team confirms the listing.
