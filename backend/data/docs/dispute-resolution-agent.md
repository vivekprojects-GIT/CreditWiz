# Dispute Resolution Agent documentation

_Version 2.3 · Owned by Cards Operations Technology · Status: Production_

## Overview

Classifies incoming card disputes by reason code, pulls the transaction, merchant and customer history, checks the dispute against scheme rules and time limits, and drafts the chargeback submission or the customer response. Routes anything ambiguous to an analyst with a summary of what has been checked.

**Why it exists.** Disputes were missing scheme deadlines because triage was manual. This classifies, checks the rules and drafts the case so analysts only handle the ambiguous ones.

## Getting started

1. Available to Cards Operations. Request the Disputes-Agent role through the access portal.
2. Open the agent from the marketplace with **Launch agent**, or from AWS Bedrock Agents directly.
3. Start with one of the example requests below, then adapt it to your case.

## What to give it and what you get back

**Input.** A dispute case ID or transaction reference and the customer's statement.

**Output.** The classified reason code, rules and deadline checks, and a draft chargeback submission or customer response.

## What you can ask

- Triage a new card dispute by reason code
- Check a dispute against scheme rules and deadlines
- Draft a chargeback submission
- Write a customer response for a declined dispute

## Capabilities

- **Case triage**
- **Rules checking**
- **Customer communication**
- **Summarisation**

## Tools, services and models

- Platform: AWS Bedrock Agents
- Tools and services: Card processor API, Scheme rules knowledge base, Case management
- Models: Claude Sonnet 5

## Limitations and guardrails

- Scheme rules are refreshed monthly; the agent shows the rule version it applied.
- Disputes with more than one reason code are routed to an analyst.

## Frequently asked questions

**Which schemes are covered?**

Visa and Mastercard consumer and commercial cards.

**What happens near a deadline?**

Cases within 5 days of a scheme deadline are flagged at the top of the queue.

## Support

Owner: **Ibrahim Khan**, Cards Operations Technology. Email [ibrahim.khan@mufg.example](mailto:ibrahim.khan@mufg.example) or use **Collaborate with the owner** on the agent page.
