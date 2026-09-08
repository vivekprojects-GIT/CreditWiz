# KYC Risk Screening Agent documentation

_Version 2.1 · Owned by Financial Crime Technology · Status: Production_

## Overview

Runs name, entity and beneficial-owner screening across sanctions lists, politically exposed person registers and adverse media. Resolves likely false positives with an explanation, assigns a preliminary risk rating, and drafts the enhanced due diligence questions an analyst should ask. Every decision is logged with its evidence for audit.

**Why it exists.** Screening hits are mostly false positives that still consumed analyst hours and delayed onboarding. This resolves the obvious ones with evidence and leaves the real ones for people.

## Getting started

1. Restricted to Financial Crime Compliance. Access is granted by the FCC platform lead after training.
2. Open the agent from the marketplace with **Launch agent**, or from AWS Bedrock Agents directly.
3. Start with one of the example requests below, then adapt it to your case.

## What to give it and what you get back

**Input.** A customer or entity name, date of birth or registration number, and country.

**Output.** A screening result: hits with match confidence, a false-positive explanation where applicable, a preliminary risk rating and suggested EDD questions.

## What you can ask

- Screen a new customer against sanctions and PEP lists
- Explain why a screening hit is likely a false positive
- Assign a preliminary customer risk rating
- Draft enhanced due diligence questions

## Capabilities

- **Sanctions screening**
- **Risk scoring**
- **Entity resolution**
- **Audit trail**

## Tools, services and models

- Platform: AWS Bedrock Agents
- Tools and services: Sanctions screening API, Adverse media feed, Case management
- Models: Claude Opus 5

## Limitations and guardrails

- False-positive explanations are advisory; the analyst confirms the disposition.
- Adverse-media coverage depends on the licensed feed refresh (daily).

## Frequently asked questions

**Which lists are screened?**

OFAC, UN, EU and UK sanctions lists, the licensed PEP register and the adverse-media feed.

**Is every decision logged?**

Yes. Each run writes the hits, the evidence and the disposition to the case audit trail.

## Support

Owner: **Daniel Okafor**, Financial Crime Technology. Email [daniel.okafor@mufg.example](mailto:daniel.okafor@mufg.example) or use **Collaborate with the owner** on the agent page.
