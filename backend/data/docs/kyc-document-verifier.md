# KYC Document Verifier documentation

_Version 1.4 · Owned by Financial Crime Technology · Status: Production_

## Overview

Reads passports, driving licences, proof-of-address and company registration documents submitted during customer onboarding. Extracts the key fields, checks them against the application, validates expiry and tamper signals, and produces a completeness report with the exact items that are missing or inconsistent. Designed to remove the first manual pass from the KYC queue.

**Why it exists.** Analysts spent the first pass of every KYC case checking whether the pack was even complete. This removes that pass so they start at judgement, not triage.

## Getting started

1. Available to Onboarding and Compliance teams. Request the KYC-Agent-User role through the access portal.
2. Open the agent from the marketplace with **Launch agent**, or from AWS Bedrock Agents directly.
3. Start with one of the example requests below, then adapt it to your case.

## What to give it and what you get back

**Input.** An onboarding case ID, or a set of uploaded identity documents (PDF, JPG, PNG).

**Output.** A completeness report: extracted fields, checks passed and failed, and the exact items to request from the customer.

## What you can ask

- Review customer onboarding documents for completeness
- Extract name, date of birth and address from identity documents
- Flag expired or inconsistent identity documents
- Prepare a KYC file for analyst sign-off

## Capabilities

- **Document extraction**
- **Identity verification**
- **Completeness checking**
- **Audit trail**

## Tools, services and models

- Platform: AWS Bedrock Agents
- Tools and services: Textract OCR, Onboarding case API, Document vault
- Models: Claude Opus 5, In-house document classifier

## Limitations and guardrails

- Does not make the final KYC decision; an analyst signs off every file.
- Handwritten documents and low-resolution scans reduce extraction accuracy; the report flags low-confidence fields.
- Supports documents in English, Spanish and Portuguese.

## Frequently asked questions

**Does it store the documents?**

No. Documents stay in the document vault; the agent reads them there and stores only the report.

**Can I re-run it after the customer sends missing items?**

Yes. Re-run on the same case and it produces an updated report showing what changed.

## Support

Owner: **Priya Raman**, Financial Crime Technology. Email [priya.raman@creditwiz.example](mailto:priya.raman@creditwiz.example) or use **Collaborate with the owner** on the agent page.
