# Policy Q&A Agent documentation

_Version 2.0 · Owned by Governance & Trust · Status: Production_

## Overview

Grounded on the approved policy library (credit, AML, data handling, complaints, acceptable use). Answers plain-language questions, always cites the policy section it relied on, and says clearly when a question is outside the library rather than guessing. Used by front-line teams and compliance alike.

**Why it exists.** Front-line staff could not find the right policy quickly and either guessed or escalated. This answers with a citation or says it does not know.

## Getting started

1. Open to all employees. Sign in with your CreditWiz account.
2. Open the agent from the marketplace with **Launch agent**, or from Internal LangGraph service directly.
3. Start with one of the example requests below, then adapt it to your case.

## What to give it and what you get back

**Input.** A plain-language question.

**Output.** An answer with citations to the policy section relied on, or a clear statement that the question is outside the policy library.

## What you can ask

- Ask what the policy says about a specific situation
- Find the policy section that applies to a customer request
- Check whether a proposed action is allowed
- Get a plain-language explanation of a regulation

## Capabilities

- **Policy lookup**
- **Grounded Q&A**
- **Citation**
- **Summarisation**

## Tools, services and models

- Platform: Internal LangGraph service
- Tools and services: Policy library, Enterprise search index
- Models: Claude Sonnet 5

## Limitations and guardrails

- Answers only from the approved policy library; it will say when a question is outside it.
- Policy updates appear in answers within one hour of publication.

## Frequently asked questions

**Can I trust the citations?**

Every citation links to the exact section. If it cannot cite, it will not answer.

**Can I ask about a specific customer?**

No. It answers policy questions only and does not access customer data.

## Support

Owner: **Tom Brennan**, Governance & Trust. Email [tom.brennan@creditwiz.example](mailto:tom.brennan@creditwiz.example) or use **Collaborate with the owner** on the agent page.
