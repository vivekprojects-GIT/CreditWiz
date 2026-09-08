# Asset Locator documentation

_Version 0.9 · Owned by Recovery Operations · Status: Pilot_

## Overview

Searches internal records and approved external data sources to locate assets, employment and current contact details linked to delinquent or charged-off accounts. Builds an evidence pack per account with source, confidence and date, so recovery teams can act on verified information rather than stale data.

**Why it exists.** Recovery teams worked from stale contact and asset data, wasting outreach. This builds a verified, sourced evidence pack per account before anyone picks up the phone.

## Getting started

1. Pilot limited to the Recovery Operations team. Contact the owner to join the pilot.
2. Open the agent from the marketplace with **Launch agent**, or from Internal LangGraph service directly.
3. Start with one of the example requests below, then adapt it to your case.

## What to give it and what you get back

**Input.** An account number or customer ID from the collections platform.

**Output.** An evidence pack: assets, employment and contact details found, each with source, confidence and date.

## What you can ask

- Locate assets linked to a charged-off account
- Find current address and employer for a delinquent customer
- Build an evidence pack for legal recovery
- Prioritise recovery accounts by recoverable value

## Capabilities

- **Asset discovery**
- **Entity resolution**
- **Evidence packaging**
- **Prioritisation**

## Tools, services and models

- Platform: Internal LangGraph service
- Tools and services: Credit bureau connector, Public records search, Collections platform
- Models: Claude Opus 5

## Limitations and guardrails

- Only approved data sources are queried; results are for internal use in line with the fair-collections policy.
- Pilot: coverage is limited to accounts charged off in the last 24 months.

## Frequently asked questions

**How current is the data?**

Each item shows its source date. Most bureau data is refreshed weekly.

**Can I export the evidence pack?**

Yes, as PDF or directly into the collections platform case.

## Support

Owner: **Marcus Lee**, Recovery Operations. Email [marcus.lee@mufg.example](mailto:marcus.lee@mufg.example) or use **Collaborate with the owner** on the agent page.
