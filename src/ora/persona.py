"""Persona + reference loading and system-prompt assembly.

PERSONA.md and REFERENCE.md are the *stable* part of the system prompt — they
should be marked for prompt caching by callers. Runtime context (today, charts,
thread history) goes in a separate block that changes every call.
"""

from dataclasses import dataclass
from datetime import date
from functools import lru_cache

from ora import config


@lru_cache(maxsize=1)
def load_persona() -> str:
    return config.PERSONA_PATH.read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def load_reference() -> str:
    return config.REFERENCE_PATH.read_text(encoding="utf-8")


def stable_system_prompt() -> str:
    """The cache-friendly part — PERSONA + REFERENCE. Identical across calls."""
    return f"{load_persona()}\n\n---\n\n{load_reference()}"


# Per-surface response shape. Drives the strict length / register instruction
# we inject every call. Override `deep=True` to relax the limits.
SURFACE_SHAPE = {
    "daily_post": (
        "1–3 short sentences. Plus the date marker header. Casual, witty, "
        "public-facing — like the funniest thing in the group chat that morning."
    ),
    "channel_mention": (
        "1–3 short sentences. A take, not a report. If the question is repetitive "
        "or already half-answered by the chart, be even shorter. One sharp call beats "
        "three soft ones."
    ),
    "thread_reply": (
        "1–3 short sentences. You're inside an ongoing thread — assume context, "
        "don't re-establish it."
    ),
    "dm": (
        "2–4 short sentences. Slightly more room because it's private, but still "
        "short and chatty. Don't lecture. If they want more, they'll ask."
    ),
    "huddle_thread": (
        "1–2 sentences max. A small drop-in, not a reading."
    ),
}

DEEP_SHAPE = (
    "Up to ~250 words. The asker has asked for depth — give it. Still no padding, "
    "no disclaimers, no recap. Lead with the call; support it with the placements "
    "that actually drove it. Skip placements that didn't drive anything."
)


@dataclass
class RuntimeContext:
    today: date
    surface: str                       # daily_post|channel_mention|thread_reply|dm|huddle_thread
    clone_chart: str                   # markdown summary of clone's chart + today's transits
    user_name: str | None = None
    user_chart: str | None = None      # markdown summary, or None if no chart on file
    thread_context: str | None = None  # last N messages, formatted
    deep: bool = False                 # set when the asker explicitly wants depth

    def render(self) -> str:
        no_chart = (
            "No chart on file. You can offer to set one up via `/ora setup` if it "
            "fits the moment — don't push it."
        )
        shape = DEEP_SHAPE if self.deep else SURFACE_SHAPE.get(
            self.surface, SURFACE_SHAPE["channel_mention"]
        )
        return (
            "## Runtime context\n\n"
            f"- **Today**: {self.today.isoformat()}\n"
            f"- **Surface**: {self.surface}\n\n"
            "### Response shape (obey this)\n"
            f"{shape}\n\n"
            "Use the chart data below as *reference*, not as a script. Pick the one "
            "or two things that actually answer the question; ignore the rest. "
            "Never recite placements that aren't doing work in your answer.\n\n"
            "### clone's chart\n"
            f"{self.clone_chart}\n\n"
            f"### Asker: {self.user_name or 'unknown'}\n"
            f"{self.user_chart or no_chart}\n\n"
            "### Recent conversation\n"
            f"{self.thread_context or '(none)'}\n"
        )
