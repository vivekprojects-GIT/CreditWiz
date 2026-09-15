## Overview

Covers the Customer Identification Program stage of a KYC review. It checks identity documents, entity formation documents and the list of authorised persons for the client.

> [!INFO] One of the review specialists
> The KYC Supervisor Agent delegates the CIP stage to this agent and brings its result into the case view.

## Getting started

1. Open to all employees. Sign in with your MUFG account.
2. Find the CIP Agent in the AI Marketplace under **KYC Workflow**.
3. Start with one of the requests below, then adapt it to your case.

## What to give it and what you get back

**Input.** Identity documents, entity formation documents and the list of authorised persons for the client.

**Output.** The result of the CIP checks, with any document that is missing or needs attention.

## What you can ask

- Verify a client's identity documents
- Check entity formation documents
- Confirm the authorised persons for an entity

## Capabilities

- **Identity verification**
- **Document extraction**
- **Completeness checking**
- **Cited source annotation**

## Where it fits in the workflow

The KYC Supervisor Agent delegates the CIP stage to it and aggregates the result into the case view. A gap it finds leads to a follow-up drafted by the Email Drafting Agent. The KYC Completeness Agent checks that this stage has reported OK before the case is closed.

## Platform, tools and models

> [!NOTE] To be confirmed
> The platform, tools and models behind this agent will be listed here once the KYC Programme confirms them.

## Limitations and guardrails

- It checks the documents on the case. A reviewer decides whether identification is complete.
- This agent is in development. Check its output before relying on it.

## Frequently asked questions

**Does it cover individuals and entities?**

Yes. It checks identity documents for people and formation documents for entities, and confirms the authorised persons.

**What happens when a document is missing?**

It reports the gap to the supervisor, which asks for a follow-up to the client.

## Support

The **KYC Programme** owns this agent. Named contacts will appear here once the owning team confirms the listing.
