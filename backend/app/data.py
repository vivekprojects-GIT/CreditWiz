"""Authored hub navigation and sample announcements. Catalogs live in backend/data."""

from .models import Link, Notification, Pillar, Section, PillarSearch

PILLARS = [
    Pillar(
        id="marketplace",
        number=1,
        title="AI Marketplace and Discovery",
        short_title="Discover",
        card_title="Discover AI",
        description="Find trusted solutions, agents and reusable capabilities.",
        icon="search",
        tone="blue",
        priority=True,
        primary_links=[
            Link(label="AI solutions", href="/marketplace/solutions"),
            Link(label="Agents", href="/marketplace/agents"),
            Link(label="Capabilities", href="/marketplace/capabilities"),
        ],
        secondary_links=[
            Link(label="Search by business domain", href="/marketplace/agents")
        ],
        cta_label="Explore marketplace",
        cta_href="/marketplace",
        search=PillarSearch(
            placeholder='Describe what you need',
            action='Find agents',
            examples=[],
        ),
        sections=[
            Section(
                title="AI solutions",
                href="/marketplace/solutions",
                blurb="Approved, production-ready AI solutions you can adopt today.",
            ),
            Section(
                title="Agents",
                href="/marketplace/agents",
                blurb="Reusable agents with owners, SLAs and usage guidance.",
            ),
            Section(
                title="Capabilities",
                href="/marketplace/capabilities",
                blurb="Platform capabilities such as document intelligence, summarisation and search.",
            ),
        ],
    ),
    Pillar(
        id="learning",
        number=2,
        title="AI Learning and Enablement",
        short_title="Learning",
        card_title="Learning",
        description="Find learning and guidance for your role.",
        icon="graduation",
        tone="teal",
        priority=True,
        primary_links=[
            Link(label="Catalog", href="/learning/catalog"),
            Link(label="Role-based paths", href="/learning/paths"),
        ],
        secondary_links=[
            Link(label="Getting started", href="/learning?path=getting-started"),
            Link(label="Best practices", href="/learning/best-practices"),
            Link(label="Product docs", href="/learning/docs"),
            Link(label="Quick reference", href="/learning/quick-reference"),
        ],
        cta_label="Explore learning",
        cta_href="/learning",
        search=PillarSearch(
            placeholder='Search learning',
            action='Find learning',
            examples=[],
        ),
        sections=[
            Section(
                title="Learning catalog",
                href="/learning/catalog",
                blurb="Courses, guides and documentation.",
            ),
            Section(
                title="Role-based paths",
                href="/learning/paths",
                blurb="Curated paths for analysts, engineers, managers and operations.",
            ),
            Section(
                title="Getting started",
                href="/learning?path=getting-started",
                blurb="Your first hour with AI at MUFG.",
            ),
            Section(
                title="Best practices",
                href="/learning/best-practices",
                blurb="How our teams get reliable results.",
            ),
            Section(
                title="Product docs",
                href="/learning/docs",
                blurb="Reference documentation for hub tools.",
            ),
            Section(
                title="Quick reference",
                href="/learning/quick-reference",
                blurb="One-page cheat sheets.",
            ),
        ],
    ),
]

NOTIFICATIONS = [
    Notification(
        id="mvp-marketplace-v1",
        title="Explore the AI Marketplace",
        body="Find agents for your work and request access in a couple of clicks.",
        href="/marketplace",
        created_at="2026-09-08T12:00:00Z",
    ),
    Notification(
        id="mvp-learning-v1",
        title="Follow your learning path",
        body="Work through your role's learning path and track your progress.",
        href="/learning/paths",
        created_at="2026-09-08T12:00:00Z",
    ),
]
