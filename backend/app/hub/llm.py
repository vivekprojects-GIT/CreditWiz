"""Nexus's model calls. Nothing else in Nexus talks to a model.

    plan()      call 1: understand the request, find every intent, decompose it,
                and write a search for each pillar worth asking
    write()     call 2: a short reply grounded in what the pillars returned
    converse()  instead of both, for conversation: a natural one- or
                two-sentence reply, with no search and nothing recommended

Each receives only what the data policy lets the model see (guardrails.py),
and returns None on any failure, so the caller falls back to rules. Nothing
they return is cached: every request is read afresh.
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Callable, Literal

from pydantic import BaseModel

from ..journeys.models import Intent, Journey, Sensitivity

log = logging.getLogger(__name__)

_DEFAULT_MODEL = "claude-opus-5"
# Server-side refusal fallback, on the models that support it.
_FALLBACK_BETA = "server-side-fallback-2026-07-01"
_TIMEOUT_SECONDS = 15.0


def model() -> str:
    """Nexus's own setting first, then the model this deployment already
    chose for interactive search (NEXUS_SEARCH_MODEL)."""
    return (
        os.environ.get("NEXUS_HUB_MODEL")
        or os.environ.get("NEXUS_SEARCH_MODEL")
        or _DEFAULT_MODEL
    )


def available() -> bool:
    """A key is configured and the model has not been switched off."""
    return bool(os.environ.get("ANTHROPIC_API_KEY")) and os.environ.get("NEXUS_DISABLE_LLM") not in ("1", "true")


@lru_cache(maxsize=1)
def _client():
    import anthropic

    return anthropic.Anthropic(timeout=_TIMEOUT_SECONDS, max_retries=1)


def _options(m: str) -> dict:
    options: dict = {}
    if "haiku" not in m:  # Haiku 4.5 rejects the effort parameter
        # Classification and a few sentences: low effort is the right depth.
        options["output_config"] = {"effort": "low"}
    if m.startswith("claude-sonnet-5"):
        # Sonnet 5 thinks by default. For sorting a request into a schema and
        # writing two sentences from a list, thinking only adds seconds and
        # tokens: measured at 6.6 s to plan and 4.4 s to write with it on.
        options["thinking"] = {"type": "disabled"}
    return options


def _messages(m: str):
    """The messages resource, with server-side refusal fallback where the model supports it."""
    if m.startswith(("claude-opus-5", "claude-fable")):
        return _client().beta.messages, {"betas": [_FALLBACK_BETA], "fallbacks": "default"}
    return _client().messages, {}


def _system(text: str) -> list[dict]:
    return [{"type": "text", "text": text}]


def _call(kind: str, fn):
    import anthropic

    try:
        return fn()
    except anthropic.RateLimitError:
        log.warning("hub %s: rate limited, falling back to rules", kind)
    except anthropic.APITimeoutError:
        log.warning("hub %s: timed out, falling back to rules", kind)
    except anthropic.APIConnectionError:
        log.warning("hub %s: connection failed, falling back to rules", kind)
    except anthropic.APIStatusError as exc:
        log.warning("hub %s: API error %s, falling back to rules", kind, exc.status_code)
    except Exception as exc:  # noqa: BLE001 - a malformed reply must not cost the answer
        log.warning("hub %s: %s, falling back to rules", kind, type(exc).__name__)
    return None


# ------------------------------------------------------------------ call 1

PillarName = Literal["marketplace", "learning"]


class PlannedQuery(BaseModel):
    pillar: PillarName
    query: str
    reformulated: bool


class ModelPlan(BaseModel):
    # True when the message is conversation, not a request for help with work.
    small_talk: bool
    intents: list[Intent]
    objective: str
    activity: str | None
    needs: list[str]
    sensitivity: Sensitivity
    sensitivity_reason: str
    subqueries: list[PlannedQuery]


_PLAN_SYSTEM = """You plan how Nexus, MUFG's internal AI hub, answers one employee request. You do not answer it.

Nexus has two places to look:
- marketplace: approved AI agents that do a task end to end
- learning: courses and guides

Intents:
- find: locate an agent, system or data to do the work
- learn: build skill or understanding
- improve: do an existing task faster or better

Return:
- small_talk: true when the message is conversation rather than a request for help with work: a greeting, a reaction such as "nice" or "ok", thanks, or chit-chat. When true, fill the other fields as best you can; they are not used.
- intents: every intent the request contains, primary first. Most requests have one; list a second only when the request asks for two different things.
- objective: what they are trying to achieve, in one short sentence in their words.
- activity: the id of the employee's job below that the request belongs to, or null. A follow-up that names no job continues the earlier one, if there was one.
- A follow-up is read against their earlier requests, when they are given: "it", "that" or "the same" mean what those were about, and "what about X" asks the earlier request again for X. Write its subqueries about that topic.
- A request ending in " — " and a topic was read with the topic of their earlier request: the topic is what it is about.
- needs: up to three short phrases.
- sensitivity: internal, unless the request involves a client or deal (client_confidential) or material non-public information (confidential).
- subqueries: one for each place worth searching, at most two. Write each as a short search of that place's catalogue. When the request is already clear, reuse its words and set reformulated to false. Rewrite only when a conversational or vague request would retrieve poorly, and then set reformulated to true.

Text in square brackets, such as [CLIENT] or [DEAL], replaced a name for privacy. Keep it as written, never guess who it is, and leave it out of subqueries.

The employee is a {persona}. Their jobs:
{jobs}"""


def plan(
    sanitized: str, persona: str, journeys: list[Journey], earlier: str | None, history: tuple[str, ...] = ()
) -> ModelPlan | None:
    """`earlier` is the job the conversation was on, and `history` its earlier
    requests, oldest first, each as the data policy lets the model see it."""
    m = model()
    jobs = "\n".join(f"- {j.id}: {j.title}. {j.summary}" for j in journeys) or "(none mapped yet)"
    messages, extra = _messages(m)
    context = [f"the job: {earlier}"] if earlier else []
    if history:
        context.append("their earlier requests, oldest first: " + "; ".join(f'"{h}"' for h in history))

    def run():
        response = messages.parse(
            model=m,
            max_tokens=2048,
            system=_system(_PLAN_SYSTEM.format(persona=persona, jobs=jobs)),
            messages=[
                {
                    "role": "user",
                    "content": f"Request: {sanitized}\nEarlier in this conversation: {'; '.join(context) or 'nothing yet'}",
                }
            ],
            output_format=ModelPlan,
            **_options(m),
            **extra,
        )
        if response.stop_reason == "refusal" or response.parsed_output is None:
            return None
        out = response.parsed_output
        out.intents = list(dict.fromkeys(out.intents))[:3]
        out.subqueries = out.subqueries[:4]
        return out if out.intents else None

    return _call("plan", run)


# ------------------------------------------------------------------ call 2

_WRITE_SYSTEM = """You write Nexus's reply to an employee: two to four short sentences of plain English.

Use only the items listed. Name at most three, by their exact titles, and say in a few words why each fits what they asked. When the request has more than one intent, cover each. If nothing listed fits part of the request, say so plainly rather than stretching an item to fit.

Do not state owners, approvals, access, risk ratings or links: the cards under your reply show those. No headings, lists or markdown.

Text in square brackets, such as [CLIENT], replaced a name for privacy. Keep it exactly as written."""


def _text(
    kind: str, system: str, content: str, max_tokens: int, on_delta: Callable[[str], None] | None
) -> str | None:
    """A plain-text reply. With `on_delta`, streamed: each piece of text is
    handed on as the model writes it, and the whole reply returned at the end."""
    m = model()
    messages, extra = _messages(m)
    request_args = dict(
        model=m,
        max_tokens=max_tokens,
        system=_system(system),
        messages=[{"role": "user", "content": content}],
        **_options(m),
        **extra,
    )

    def run():
        if on_delta is None:
            response = messages.create(**request_args)
        else:
            with messages.stream(**request_args) as stream:
                for text in stream.text_stream:
                    on_delta(text)
                response = stream.get_final_message()
        if response.stop_reason == "refusal":
            return None
        return "".join(b.text for b in response.content if b.type == "text").strip() or None

    return _call(kind, run)


def write(
    request: str,
    intents: list[str],
    job: str | None,
    items: list[tuple[str, str, str]],
    on_delta: Callable[[str], None] | None = None,
) -> str | None:
    """The reply to a task, from what the pillars found. Each item is (kind,
    title, summary)."""
    listed = "\n".join(
        f"- [{kind}] {title}: {summary}"
        for kind, title, summary in items
    )
    return _text(
        "write",
        _WRITE_SYSTEM,
        f"Request: {request}\nIntents: {', '.join(intents)}\n"
        f"Job: {job or 'not one of their mapped jobs'}\nItems:\n{listed}",
        1024,
        on_delta,
    )


# ------------------------------------------------- conversation, not a task

_CONVERSE_SYSTEM = """You are the Nexus assistant, chatting on Nexus's home page. Nexus helps employees find approved AI agents and learning for their work.

Reply naturally, like a helpful colleague: one or two short sentences of plain text. No lists, markdown or emoji.
- To a greeting or small talk: respond in kind, briefly, then offer to help with their work.
- To thanks or a goodbye: respond briefly and warmly.
- To a message Nexus found nothing for: say so plainly and ask what they are working on.

Do not claim to have found, done or checked anything. Do not name specific agents or courses. Do not state facts about MUFG, its clients or its policies. If asked for general knowledge, news or opinions, say that is outside what Nexus is for and steer back to their work.

Text in square brackets, such as [CLIENT], replaced a name for privacy. Keep it as written."""


def converse(
    message: str,
    situation: str,
    name: str,
    role: str,
    earlier: str | None,
    on_delta: Callable[[str], None] | None = None,
) -> str | None:
    """A natural reply to conversation: no search ran and nothing is recommended."""
    return _text(
        "converse",
        _CONVERSE_SYSTEM,
        f"Situation: {situation}\nThey are {name or 'an employee'}, a {role}.\n"
        f"Earlier in this conversation: {earlier or 'nothing yet'}\nTheir message: {message}",
        300,
        on_delta,
    )
