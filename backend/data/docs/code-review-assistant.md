# Code Review Assistant documentation

_Version 4.2 · Owned by Developer Platform · Status: Production_

## Overview

Runs on every pull request in approved repositories. Flags likely bugs, insecure patterns, missing tests and deviations from the engineering standards, and explains each finding with a suggested fix. Engineers can also ask it to explain unfamiliar code or draft the PR description.

**Why it exists.** Review load on senior engineers slowed every release. This catches the routine defects and standards issues first so human review focuses on design.

## Getting started

1. Enabled automatically on repositories in the approved GitHub organisation. Ask Developer Platform to onboard a repo.
2. Open the agent from the marketplace with **Launch agent**, or from GitHub Actions + Internal LangGraph service directly.
3. Start with one of the example requests below, then adapt it to your case.

## What to give it and what you get back

**Input.** A pull request in an onboarded repository.

**Output.** Inline review comments with severity and a suggested fix, plus an optional draft PR description.

## What you can ask

- Review a pull request for bugs and security issues
- Check code against MUFG engineering standards
- Explain an unfamiliar piece of code
- Draft a pull request description

## Capabilities

- **Code review**
- **Security analysis**
- **Documentation generation**
- **Test generation**

## Tools, services and models

- Platform: GitHub Actions + Internal LangGraph service
- Tools and services: GitHub, SonarQube, Engineering standards index
- Models: Claude Opus 5

## Limitations and guardrails

- Runs only on repositories onboarded by Developer Platform.
- Findings are advisory; branch protection rules still decide what merges.

## Frequently asked questions

**How do I onboard a repository?**

Ask Developer Platform in the #dev-platform channel; onboarding takes about a day.

**Can I turn off a rule?**

Yes, per repository, through the .mufg-review.yml file.

## Support

Owner: **Ravi Menon**, Developer Platform. Email [ravi.menon@mufg.example](mailto:ravi.menon@mufg.example) or use **Collaborate with the owner** on the agent page.
