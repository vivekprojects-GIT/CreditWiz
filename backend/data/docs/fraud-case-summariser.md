# Fraud Case Summariser documentation

_Version 1.7 · Owned by Fraud Analytics · Status: Production_

## Overview

Reads alerts, transaction history, device and login signals, and analyst notes for a fraud case and produces a structured brief: what happened, what is unusual, what has been checked, and a recommended action. Helps investigators start from understanding instead of raw data.

**Why it exists.** Investigators lost the first 20 minutes of every case reading raw alerts. This gives them a structured brief and a recommended next step instead.

## Getting started

1. Restricted to Fraud Operations and Fraud Analytics. Access managed by the Fraud platform lead.
2. Open the agent from the marketplace with **Launch agent**, or from AWS Bedrock Agents directly.
3. Start with one of the example requests below, then adapt it to your case.

## What to give it and what you get back

**Input.** A fraud case ID.

**Output.** A structured brief: what happened, what is unusual, what has been checked, and a recommended next step.

## What you can ask

- Summarise an open fraud case for an investigator
- Explain what is unusual in a set of transactions
- Recommend the next investigation step
- Prepare a case brief for the fraud review meeting

## Capabilities

- **Case summarisation**
- **Anomaly detection**
- **Investigation support**
- **Risk scoring**

## Tools, services and models

- Platform: AWS Bedrock Agents
- Tools and services: Fraud alert platform, Transaction warehouse, Device intelligence
- Models: Claude Opus 5

## Limitations and guardrails

- The brief summarises evidence already in the case; it does not pull new data.
- Recommendations are suggestions, never automatic actions.

## Frequently asked questions

**Can I ask follow-up questions?**

Yes. After the brief you can ask about any signal it mentions.

**Does it close cases?**

No. It only summarises and recommends.

## Support

Owner: **Elena Petrova**, Fraud Analytics. Email [elena.petrova@mufg.example](mailto:elena.petrova@mufg.example) or use **Collaborate with the owner** on the agent page.
