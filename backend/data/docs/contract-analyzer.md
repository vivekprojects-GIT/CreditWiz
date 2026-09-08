# Contract Analyzer documentation

_Version 3.0 · Owned by Legal Technology · Status: Production_

## Overview

Ingests supplier, partner and customer contracts, identifies the clause types that matter to MUFG (termination, liability, data protection, pricing, SLAs), compares them with the approved playbook and highlights deviations. Produces a one-page summary and a clause table that legal and procurement can review in minutes.

**Why it exists.** Legal review queues were the slowest step in supplier onboarding. This turns a 40-page contract into a one-page summary and clause table so lawyers review exceptions, not everything.

## Getting started

1. Open to all employees. Sign in with your MUFG account.
2. Open the agent from the marketplace with **Launch agent**, or from Azure AI Foundry directly.
3. Start with one of the example requests below, then adapt it to your case.

## What to give it and what you get back

**Input.** A contract file (PDF or DOCX) and, optionally, the playbook to compare against.

**Output.** A one-page summary, a clause table with playbook deviations highlighted, and a list of questions for legal.

## What you can ask

- Summarise a supplier contract before signature
- Extract termination, liability and data-protection clauses
- Compare contract terms with the approved playbook
- Find non-standard terms across a set of agreements

## Capabilities

- **Document extraction**
- **Clause classification**
- **Summarisation**
- **Playbook comparison**

## Tools, services and models

- Platform: Azure AI Foundry
- Tools and services: Contract repository, Playbook service, SharePoint
- Models: GPT-5, Claude Sonnet 5

## Limitations and guardrails

- Playbook comparison covers the clause types listed in the playbook; other clauses are summarised only.
- Scanned contracts without a text layer are OCR'd first and may need a manual check.

## Frequently asked questions

**Can I upload a batch?**

Yes, up to 25 contracts at once; results arrive as they complete.

**Does it negotiate?**

No. It summarises and compares. Redlines are drafted by legal.

## Support

Owner: **Hannah Weiss**, Legal Technology. Email [hannah.weiss@mufg.example](mailto:hannah.weiss@mufg.example) or use **Collaborate with the owner** on the agent page.
