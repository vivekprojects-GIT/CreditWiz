## Overview

Watches the AMT mailbox for client replies, picks them up automatically, classifies the documents attached to them, and routes each one to the specialist agent that needs it. It removes the manual triage between a client responding and the review continuing.

> [!INFO] The front door of the KYC workflow
> Every client reply enters the workflow here, before any specialist sees it.

## Getting started

1. Open to all employees. Sign in with your MUFG account.
2. Find the Client Response Analyzer Agent in the AI Marketplace under **KYC Workflow**.
3. Start with one of the requests below, then adapt it to your case.

## What to give it and what you get back

**Input.** Client replies arriving in the AMT mailbox, with their attachments.

**Output.** Each attached document classified and routed to the case and the specialist that needs it.

## What you can ask

- Pick up a client response from the AMT mailbox automatically
- Classify documents attached to a client reply
- Route an incoming document to the right specialist agent

## Capabilities

- **Document classification**
- **Document extraction**
- **Workflow orchestration**
- **Cited source annotation**

## Where it fits in the workflow

It sits at the start. Replies arrive in the AMT mailbox after the Email Drafting Agent's request reaches the client. This agent classifies each document and routes it to the case the KYC Supervisor Agent is running, which hands it to the right specialist.

## Platform, tools and models

> [!NOTE] To be confirmed
> The platform, tools and models behind this agent will be listed here once the KYC Programme confirms them.

## Limitations and guardrails

- It classifies and routes documents; it does not review their content.
- Spot-check how documents are classified while the agent is in development.

## Frequently asked questions

**Which mailbox does it watch?**

The AMT mailbox, where client replies for the KYC workflow arrive.

**Does it reply to the client?**

No. Replies to the client are drafted by the Email Drafting Agent and sent by a person.

## Support

The **KYC Programme** owns this agent. Named contacts will appear here once the owning team confirms the listing.
