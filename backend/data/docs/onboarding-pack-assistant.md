# Customer Onboarding Assistant documentation

_Version 1.0 · Owned by Onboarding Experience · Status: Beta_

## Overview

Reviews the full onboarding pack for a new customer, checks that every required document and data point is present, drafts the follow-up email for anything missing, and hands a decision-ready summary to the onboarding analyst. Works with the KYC Document Verifier for identity checks.

**Why it exists.** Applications bounced back and forth with customers over missing items. This catches gaps up front and drafts the request, cutting time-to-decision.

## Getting started

1. Beta for onboarding teams. Request access via the Onboarding Experience team channel.
2. Open the agent from the marketplace with **Launch agent**, or from Microsoft Agent 365 directly.
3. Start with one of the example requests below, then adapt it to your case.

## What to give it and what you get back

**Input.** An onboarding application ID.

**Output.** A gap list, a draft follow-up email, and a decision-ready summary for the analyst.

## What you can ask

- Check a new customer application for missing information
- Draft a follow-up email requesting missing documents
- Summarise an onboarding file for the decision maker
- Track onboarding cases that are waiting on the customer

## Capabilities

- **Completeness checking**
- **Customer communication**
- **Summarisation**
- **Case triage**

## Tools, services and models

- Platform: Microsoft Agent 365
- Tools and services: Onboarding case API, Outlook, Document vault
- Models: GPT-5

## Limitations and guardrails

- Beta: templates are available for personal and small-business applications only.
- Follow-up emails are drafts; the analyst reviews and sends.

## Frequently asked questions

**Does it contact the customer?**

It drafts the email; the analyst sends it.

**How does it relate to the KYC Document Verifier?**

It calls the verifier for identity checks and includes the result in the summary.

## Support

Owner: **Sofia Alvarez**, Onboarding Experience. Email [sofia.alvarez@mufg.example](mailto:sofia.alvarez@mufg.example) or use **Collaborate with the owner** on the agent page.
