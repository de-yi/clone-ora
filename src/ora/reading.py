"""Helpers shared by handlers: assemble runtime context, call the LLM,
fall back gracefully when something breaks.
"""

import logging
from datetime import date, datetime
from zoneinfo import ZoneInfo

from ora import config, llm, subjects
from ora.charts import render
from ora.persona import RuntimeContext

logger = logging.getLogger(__name__)

FALLBACK = "Mm. The chart's there but I can't reach the words right now. Try me in a minute."


def today_local() -> date:
    """Today in ORA_TIMEZONE."""
    return datetime.now(ZoneInfo(config.ORA_TIMEZONE)).date()


def clone_chart_block() -> str:
    """clone's static chart + today's day pillar / transits, joined."""
    clone_md = subjects.clone_chart_markdown()
    today_md = render.render_today(today_local(), tz=config.ORA_TIMEZONE)
    return f"{clone_md}\n\n{today_md}"


def user_chart_block(slack_user_id: str) -> str | None:
    row = subjects.get_by_slack_id(slack_user_id)
    if not row:
        return None
    return subjects.render_subject_markdown(row["id"])


# Heuristic: if the asker uses any of these phrases, ora should give a longer
# reading. Kept simple; better to occasionally miss than to gate too narrowly.
_DEEP_TRIGGERS = (
    "deep read", "deep reading", "long read", "full reading", "in depth",
    "in-depth", "tell me more", "go deeper", "explain", "why",
    "what does that mean", "more detail", "/ora deep",
)


def _wants_deep(user_message: str) -> bool:
    m = user_message.lower()
    return any(trigger in m for trigger in _DEEP_TRIGGERS)


def respond(
    user_message: str,
    *,
    surface: str,
    slack_user_id: str | None,
    user_display_name: str | None = None,
    slack_channel_id: str | None = None,
    slack_thread_ts: str | None = None,
    slack_message_ts: str | None = None,
    deep: bool | None = None,
) -> str:
    """Build runtime context, call ora, return the text response (or a fallback).

    `deep=None` (default) auto-detects from the message text. Pass deep=True/False
    explicitly to override.
    """
    if deep is None:
        deep = _wants_deep(user_message)

    user_chart = user_chart_block(slack_user_id) if slack_user_id else None
    user_subject_row = subjects.get_by_slack_id(slack_user_id) if slack_user_id else None
    user_subject_id = user_subject_row["id"] if user_subject_row else None

    runtime = RuntimeContext(
        today=today_local(),
        surface=surface,
        clone_chart=clone_chart_block(),
        user_name=user_display_name,
        user_chart=user_chart,
        thread_context=None,  # TODO: fetch last N from conversations.history
        deep=deep,
    )

    try:
        return llm.read(
            user_message,
            runtime,
            deep=deep,
            subject_id=user_subject_id,
            slack_channel_id=slack_channel_id,
            slack_thread_ts=slack_thread_ts,
            slack_message_ts=slack_message_ts,
        )
    except Exception:
        logger.exception("LLM call failed; returning fallback")
        return FALLBACK
