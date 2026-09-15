"""Architecture pages for every agent, derived from the catalogue.

A pattern supplies the shape of the system: who uses it, the steps a request
goes through, the design principles. The agent supplies the specifics: its
platform, models, tools and systems of record, straight from agents.json.

Nothing is invented. A component the owning team has not confirmed is shown as
"To be confirmed", and the page carries a Draft status until the agent is in
production. The diagram is returned as data rather than an image, so it renders
crisply at any size and cannot drift from the catalogue it describes.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel

from .models import Agent

TBC = "To be confirmed"
KYC_CATEGORY = "KYC Workflow"

NodeKind = Literal["person", "external", "channel", "agent", "model", "tool", "store"]


class ArchNode(BaseModel):
    id: str
    label: str
    detail: str = ""
    kind: NodeKind
    highlight: bool = False


class ArchGroup(BaseModel):
    label: str = ""
    nodes: list[ArchNode]


class ArchColumn(BaseModel):
    id: str
    label: str
    sublabel: str = ""
    groups: list[ArchGroup]


class ArchEdge(BaseModel):
    source: str
    target: str
    step: int | None = None
    dashed: bool = False


class ArchBandItem(BaseModel):
    label: str
    detail: str = ""


class ArchStep(BaseModel):
    number: int
    title: str
    detail: str


class ArchComponent(BaseModel):
    name: str
    type: str
    responsibility: str


class AgentRef(BaseModel):
    id: str
    name: str


class ArchitecturePage(BaseModel):
    agent_id: str
    agent_name: str
    title: str
    pattern: str
    status: str
    owner: str
    team: str
    version: str
    updated: str
    summary: str
    confirmed: bool
    columns: list[ArchColumn]
    edges: list[ArchEdge]
    band: list[ArchBandItem]
    steps: list[ArchStep]
    components: list[ArchComponent]
    principles: list[str]
    related: list[AgentRef]
    source_kind: str


def page_status(agent: Agent) -> str:
    """Confluence-style page status from where the agent is in its lifecycle."""
    if agent.status == "production":
        return "Verified"
    if agent.status in ("pilot", "beta"):
        return "In review"
    return "Draft"


KIND_LABEL = {
    "person": "Person",
    "external": "External party",
    "channel": "Channel",
    "agent": "Agent",
    "model": "Model",
    "tool": "Tool",
    "store": "System of record",
}

PERSON_LABEL = {
    "compliance_user": "Compliance analyst",
    "business_user": "Business user",
    "relationship_manager": "Relationship manager",
    "risk_analyst": "Risk analyst",
    "operations_user": "Operations analyst",
    "developer": "Engineer",
}

# Names that describe where data lives rather than something the agent calls.
_STORE_HINTS = (
    "repository",
    "vault",
    "warehouse",
    "library",
    "index",
    "knowledge base",
    "platform",
    "sharepoint",
    "case management",
)


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _article(word: str) -> str:
    return "An" if word[:1].lower() in "aeiou" else "A"


def _join(names: list[str]) -> str:
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + " and " + names[-1]


# ---------------------------------------------------------------- patterns
#
# Each pattern names the six phases of a request. A phase is only drawn and
# listed when the agent actually has the components it involves, so an agent
# with no tools never shows an empty "call tools" step.

PATTERNS: dict[str, dict] = {
    "Document agent": {
        "summary": "Reads documents, extracts structured fields, checks them against a source of truth and reports gaps.",
        "phases": {
            "request": ("Submit documents", "{Person} submits documents in the MUFG AI Hub."),
            "invoke": ("Invoke the agent", "The hub calls {agent} with references to the documents. Documents stay where they are stored; nothing is copied."),
            "reason": ("Extract", "The model reads each page into a typed schema. Every field carries a confidence score, and low confidence is surfaced, never hidden."),
            "act": ("Validate", "Fields are checked against business rules and the source of truth through {tools}."),
            "record": ("Record findings", "Completeness and consistency findings are written to {stores}, with the evidence behind each one."),
            "review": ("Human sign-off", "A person reviews the report and signs off. The report, not raw model output, is what other systems consume."),
        },
        "principles": [
            "Keep documents in the vault; pass references, not copies.",
            "Every extracted field carries a confidence score; low confidence is surfaced, never hidden.",
            "The report, not the raw model output, is the contract with downstream systems.",
        ],
    },
    "Research agent": {
        "summary": "Plans and runs multi-step searches across approved sources, then assembles a sourced evidence pack.",
        "phases": {
            "request": ("Submit a target", "{Person} submits the account or entity to research."),
            "invoke": ("Plan the search", "{agent} decides which sources to query and in what order."),
            "reason": ("Assess findings", "The model removes duplicates and scores each finding for confidence."),
            "act": ("Query approved sources", "Allow-listed connectors query internal and external sources: {tools}."),
            "record": ("Assemble the evidence pack", "Every item in the evidence pack keeps its source and date, and the pack is stored in {stores}."),
            "review": ("Reviewer decision", "A reviewer accepts or rejects each item before it is used."),
        },
        "principles": [
            "Only approved connectors; each one is allow-listed and logged.",
            "Nothing leaves the evidence pack without a source.",
            "Long-running: results stream in as connectors complete.",
        ],
    },
    "Workflow agent": {
        "summary": "Drives a multi-step business process, calling systems and drafting outputs, with a person approving every external action.",
        "phases": {
            "request": ("Start the process", "{Person} starts a case or asks for the next step in the MUFG AI Hub."),
            "invoke": ("Load the case", "{agent} loads the case state and decides the next step from the process definition."),
            "reason": ("Draft the output", "The model drafts the next output: a message, a summary or a checklist."),
            "act": ("Call systems", "Tools read case data and check rules: {tools}."),
            "record": ("Update the case", "The approved action is carried out and the case is updated in {stores}."),
            "review": ("Human approval", "Every external action, such as sending or submitting, waits for a person to approve it."),
        },
        "principles": [
            "The process definition lives in configuration, not in the prompt.",
            "External side effects, such as sending or submitting, always require approval.",
            "Every step is idempotent, so a retry never duplicates work.",
        ],
    },
    "Summarisation agent": {
        "summary": "Turns a large, mixed set of case records into a structured brief with a recommended next step.",
        "phases": {
            "request": ("Select a case", "{Person} opens a case in the MUFG AI Hub."),
            "invoke": ("Gather the record", "{agent} gathers the alerts, transactions, notes and signals for the case."),
            "reason": ("Write the brief", "The model writes a structured brief against a fixed template, with every statement linked to its source."),
            "act": ("Read signals", "Signals are read from {tools}."),
            "record": ("Read case data", "Case records are read from {stores}. No new data is fetched during summarisation."),
            "review": ("Analyst follow-up", "The analyst asks follow-up questions, answered from the same case context."),
        },
        "principles": [
            "A fixed output template keeps briefs comparable across cases.",
            "Every statement is traceable to a source record.",
            "No new data is fetched during summarisation; it works on what is in the case.",
        ],
    },
    "RAG agent": {
        "summary": "Answers questions from an approved document library, with a citation on every answer.",
        "phases": {
            "request": ("Ask a question", "{Person} asks a question in the MUFG AI Hub."),
            "invoke": ("Retrieve passages", "{agent} retrieves the most relevant passages from the indexed library."),
            "reason": ("Answer with citations", "The model answers using only the retrieved passages and cites the exact sections."),
            "act": ("Search", "Retrieval runs through {tools}."),
            "record": ("Read approved sources", "Only approved, versioned documents in {stores} are indexed."),
            "review": ("Decline when unsure", "When retrieval confidence is low, the agent declines rather than guesses."),
        },
        "principles": [
            "Index only approved, versioned documents.",
            "Answers without a citation are not returned.",
            "Re-index within an hour of a document update.",
        ],
    },
    "CI agent": {
        "summary": "Runs inside the delivery pipeline on every change, producing findings that engineers act on before merge.",
        "phases": {
            "request": ("Open a pull request", "{Person} opens or updates a pull request."),
            "invoke": ("Run in the pipeline", "The pipeline runs {agent} on the change, with only the context it needs."),
            "reason": ("Review the change", "Static analysis and model review run in parallel, and findings are ranked by severity."),
            "act": ("Post findings", "Findings are posted to the pull request through {tools}."),
            "record": ("Check standards", "Findings are checked against {stores}."),
            "review": ("Engineer decides", "The engineer resolves or dismisses each finding; branch protection decides the merge."),
        },
        "principles": [
            "Advisory by default; blocking rules are opt-in per repository.",
            "Runs on the change plus minimal context to keep cost and latency low.",
            "Findings carry a rule ID so teams can tune or suppress them.",
        ],
    },
}

_STANDARD_BAND = [
    ArchBandItem(label="Single sign-on", detail="MUFG account"),
    ArchBandItem(label="Audit trail", detail="Every step logged"),
    ArchBandItem(label="Human review", detail="Before results are used"),
    ArchBandItem(label="Monitoring", detail="Quality and cost tracked"),
    ArchBandItem(label="Data protection", detail="Data stays in approved systems"),
]


def _pattern_page(agent: Agent, catalogue: list[Agent]) -> ArchitecturePage:
    pattern = PATTERNS.get(agent.architecture_pattern) or PATTERNS["Workflow agent"]
    person_label = PERSON_LABEL.get(agent.personas[0], "Business user") if agent.personas else "Business user"
    platform = agent.platform or TBC

    person = ArchNode(id="person", label=person_label, kind="person")
    channel = ArchNode(id="hub", label="MUFG AI Hub", detail="Web", kind="channel")
    me = ArchNode(id="agent", label=agent.name, detail=agent.architecture_pattern or "Agent", kind="agent", highlight=True)
    models = [ArchNode(id=f"model-{_slug(m)}", label=m, kind="model") for m in agent.models] or [
        ArchNode(id="model-tbc", label="Model", detail=TBC, kind="model")
    ]
    tools = [ArchNode(id=f"tool-{_slug(t)}", label=t, kind="tool") for t in agent.tools_services if not _is_store(t)]
    stores = [ArchNode(id=f"store-{_slug(t)}", label=t, kind="store") for t in agent.tools_services if _is_store(t)]

    groups = [ArchGroup(label="Models", nodes=models)]
    if tools:
        groups.append(ArchGroup(label="Tools and integrations", nodes=tools))
    if stores:
        groups.append(ArchGroup(label="Systems of record", nodes=stores))

    columns = [
        ArchColumn(id="users", label="Users", groups=[ArchGroup(nodes=[person])]),
        ArchColumn(id="channel", label="Channel", groups=[ArchGroup(nodes=[channel])]),
        ArchColumn(id="runtime", label="Agent runtime", sublabel=platform, groups=[ArchGroup(nodes=[me])]),
        ArchColumn(id="services", label="Models, tools and data", groups=groups),
    ]

    fill = {
        "Person": f"{_article(person_label)} {person_label.lower()}",
        "agent": agent.name,
        "tools": _join([t.label for t in tools]),
        "stores": _join([s.label for s in stores]),
    }
    phases = [
        ("request", [("person", "hub")]),
        ("invoke", [("hub", "agent")]),
        ("reason", [("agent", m.id) for m in models]),
        ("act", [("agent", t.id) for t in tools]),
        ("record", [("agent", s.id) for s in stores]),
        ("review", []),
    ]
    steps: list[ArchStep] = []
    edges: list[ArchEdge] = []
    for phase, links in phases:
        if phase in ("act", "record") and not links:
            continue
        number = len(steps) + 1
        title, detail = pattern["phases"][phase]
        steps.append(ArchStep(number=number, title=title, detail=detail.format(**fill)))
        edges += [ArchEdge(source=s, target=t, step=number) for s, t in links]

    components = [
        ArchComponent(name=person_label, type=KIND_LABEL["person"], responsibility="Starts the request and reviews the result."),
        ArchComponent(name="MUFG AI Hub", type=KIND_LABEL["channel"], responsibility="Signs the user in and passes the request to the agent."),
        ArchComponent(name=agent.name, type=KIND_LABEL["agent"], responsibility=agent.tagline),
        *[
            ArchComponent(name=m.label, type=KIND_LABEL["model"], responsibility=f"Reasons over the request. Hosted on {platform}.")
            for m in models
        ],
        *[ArchComponent(name=t.label, type=KIND_LABEL["tool"], responsibility="Called by the agent to read data or take a step.") for t in tools],
        *[ArchComponent(name=s.label, type=KIND_LABEL["store"], responsibility="Holds the records the agent reads or updates.") for s in stores],
    ]
    related = [
        AgentRef(id=a.id, name=a.name)
        for a in catalogue
        if a.id != agent.id and a.architecture_pattern == agent.architecture_pattern
    ]
    return ArchitecturePage(
        agent_id=agent.id,
        agent_name=agent.name,
        title=f"{agent.name} architecture",
        pattern=agent.architecture_pattern or "Agent",
        status=page_status(agent),
        owner=agent.owner.name,
        team=agent.owner.team,
        version=agent.version,
        updated=agent.updated_at,
        summary=pattern["summary"],
        confirmed=bool(agent.platform and agent.models),
        columns=columns,
        edges=edges,
        band=_STANDARD_BAND,
        steps=steps,
        components=components,
        principles=pattern["principles"],
        related=related,
        source_kind=agent.source_kind,
    )


def _is_store(name: str) -> bool:
    lowered = name.lower()
    return any(hint in lowered for hint in _STORE_HINTS)


# ------------------------------------------------------------ KYC workflow
#
# The client's ten KYC agents are one system: a supervisor delegating stages to
# specialists. Every page shows the whole workflow with that agent highlighted,
# because an agent in the middle of a pipeline only makes sense in context.
# Every component and step comes from the client's own descriptions.

_KYC_SPECIALISTS = (
    "kyc-cip-agent",
    "kyc-tax-agent",
    "kyc-ownership-org-chart-agent",
    "kyc-fincen-bo-form-agent",
    "kyc-sanctions-review-agent",
    "kyc-adverse-media-agent",
    "kyc-completeness-agent",
)


def _kyc_page(agent: Agent, catalogue: list[Agent]) -> ArchitecturePage:
    names = {a.id: a.name for a in catalogue}

    def node(agent_id: str) -> ArchNode:
        return ArchNode(
            id=agent_id,
            label=names.get(agent_id, agent_id),
            kind="agent",
            highlight=agent_id == agent.id,
        )

    client = ArchNode(id="client", label="Client", detail="Replies to requests", kind="external")
    analyst = ArchNode(id="analyst", label="KYC analyst", detail="Reviews and sends", kind="person")
    mailbox = ArchNode(id="amt-mailbox", label="AMT mailbox", detail="Client replies", kind="channel")
    lists = ArchNode(id="sanctions-lists", label="Sanctions lists", detail="OFAC, EU, UN, OFSI", kind="external")
    media = ArchNode(id="media-sources", label="Adverse media sources", detail="News and regulatory actions", kind="external")
    konect = ArchNode(id="konect", label="Konect", detail="KYC system of record", kind="store")

    columns = [
        ArchColumn(id="people", label="People", groups=[ArchGroup(nodes=[client, analyst])]),
        ArchColumn(
            id="intake",
            label="Intake and outreach",
            groups=[ArchGroup(nodes=[mailbox, node("kyc-client-response-analyzer"), node("kyc-email-drafting-agent")])],
        ),
        ArchColumn(id="orchestration", label="Orchestration", groups=[ArchGroup(nodes=[node("kyc-supervisor-agent")])]),
        ArchColumn(
            id="specialists",
            label="Review specialists",
            groups=[ArchGroup(nodes=[node(i) for i in _KYC_SPECIALISTS if i in names])],
        ),
        ArchColumn(id="systems", label="Data and systems", groups=[ArchGroup(nodes=[lists, media, konect])]),
    ]

    specialists = [i for i in _KYC_SPECIALISTS if i in names and i != "kyc-completeness-agent"]
    edges = [
        ArchEdge(source="client", target="amt-mailbox", step=1),
        ArchEdge(source="amt-mailbox", target="kyc-client-response-analyzer", step=2),
        ArchEdge(source="kyc-client-response-analyzer", target="kyc-supervisor-agent", step=3),
        *[ArchEdge(source="kyc-supervisor-agent", target=s, step=4) for s in specialists],
        ArchEdge(source="kyc-sanctions-review-agent", target="sanctions-lists", step=5),
        ArchEdge(source="kyc-adverse-media-agent", target="media-sources", step=5),
        ArchEdge(source="kyc-supervisor-agent", target="kyc-email-drafting-agent", step=6),
        ArchEdge(source="kyc-email-drafting-agent", target="client", step=6),
        ArchEdge(source="analyst", target="kyc-email-drafting-agent", step=7, dashed=True),
        ArchEdge(source="kyc-supervisor-agent", target="kyc-completeness-agent", step=8),
        ArchEdge(source="kyc-completeness-agent", target="konect", step=9),
    ]
    present = {n.id for c in columns for g in c.groups for n in g.nodes}
    edges = [e for e in edges if e.source in present and e.target in present]

    steps = [
        ArchStep(number=1, title="Client responds", detail="The client replies to a request for information. Replies arrive in the AMT mailbox."),
        ArchStep(number=2, title="Pick up and classify", detail="The Client Response Analyzer Agent picks the reply up automatically and classifies each attached document."),
        ArchStep(number=3, title="Route to the case", detail="Each document is routed to the case that the KYC Supervisor Agent is running."),
        ArchStep(number=4, title="Delegate each stage", detail="The supervisor delegates each review stage to the specialist that owns it and tracks which stages are outstanding."),
        ArchStep(number=5, title="Check external sources", detail="Sanctions Review screens against the OFAC, EU, UN and OFSI lists. Adverse Media searches for financial crime and regulatory actions."),
        ArchStep(number=6, title="Chase what is missing", detail="For any gap, the Email Drafting Agent drafts a request for information or a follow-up for the client."),
        ArchStep(number=7, title="Reviewer sends", detail="A KYC analyst checks each draft and sends it. No agent sends on its own."),
        ArchStep(number=8, title="Confirm completeness", detail="The KYC Completeness Agent confirms that every specialist has reported OK."),
        ArchStep(number=9, title="Populate Konect", detail="Once every stage is complete, the case is populated in Konect."),
    ]

    by_id = {a.id: a for a in catalogue}
    components = [
        ArchComponent(name="Client", type=KIND_LABEL["external"], responsibility="Provides documents and answers requests for information."),
        ArchComponent(name="KYC analyst", type=KIND_LABEL["person"], responsibility="Reviews the case and approves every outbound message."),
        ArchComponent(name="AMT mailbox", type=KIND_LABEL["channel"], responsibility="Receives client replies for the KYC workflow."),
        *[
            ArchComponent(name=n.label, type=KIND_LABEL["agent"], responsibility=by_id[n.id].tagline)
            for c in columns
            for g in c.groups
            for n in g.nodes
            if n.kind == "agent" and n.id in by_id
        ],
        ArchComponent(name="Sanctions lists", type=KIND_LABEL["external"], responsibility="OFAC, EU, UN and OFSI lists used for screening."),
        ArchComponent(name="Adverse media sources", type=KIND_LABEL["external"], responsibility="Sources searched for financial crime and regulatory actions."),
        ArchComponent(name="Konect", type=KIND_LABEL["store"], responsibility="KYC system of record, populated when a case is complete."),
    ]
    return ArchitecturePage(
        agent_id=agent.id,
        agent_name=agent.name,
        title=f"{agent.name} architecture",
        pattern="KYC workflow",
        status=page_status(agent),
        owner=agent.owner.name,
        team=agent.owner.team,
        version=agent.version,
        updated=agent.updated_at,
        summary=(
            "The KYC review, run by a supervisor agent that delegates each stage to a specialist "
            f"and aggregates the results into one case view. {agent.name} is highlighted."
        ),
        confirmed=bool(agent.platform and agent.models),
        columns=columns,
        edges=edges,
        band=[
            ArchBandItem(label="Model endpoint", detail=TBC),
            ArchBandItem(label="Agent runtime", detail=TBC),
            ArchBandItem(label="Single sign-on", detail="MUFG account"),
            ArchBandItem(label="Audit trail", detail="Every stage logged"),
            ArchBandItem(label="Human review", detail="Before anything is sent"),
            ArchBandItem(label="Monitoring", detail="Quality and cost tracked"),
        ],
        steps=steps,
        components=components,
        principles=[
            "Each stage is owned by one specialist; the supervisor delegates and aggregates, it does not review.",
            "Every outbound message is a draft until a person sends it.",
            "Screening results are presented for a reviewer to disposition; no agent clears a hit.",
            "A case is complete only when every specialist reports OK, and Konect is populated last.",
        ],
        related=[AgentRef(id=a.id, name=a.name) for a in catalogue if a.category == KYC_CATEGORY and a.id != agent.id],
        source_kind=agent.source_kind,
    )


def build_architecture(agent: Agent, catalogue: list[Agent]) -> ArchitecturePage:
    if agent.category == KYC_CATEGORY:
        return _kyc_page(agent, catalogue)
    return _pattern_page(agent, catalogue)
