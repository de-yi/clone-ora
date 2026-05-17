"""Anthropic client wrapper.

Two models in rotation:
  - MODEL_DEFAULT (Sonnet 4.6): channel mentions, DMs, daily fortunes, huddle notes.
  - MODEL_DEEP    (Opus 4.7):   explicitly-requested deep readings (/ora deep, etc).

Prompt caching:
  PERSONA.md + REFERENCE.md are the stable system content. We mark them with
  cache_control so repeat calls hit the cache (5-minute TTL on the Anthropic
  side; the daily fortune cron and active conversations both benefit).
"""

import logging

from anthropic import Anthropic

from ora import config, db
from ora.persona import RuntimeContext, stable_system_prompt

logger = logging.getLogger(__name__)

_client: Anthropic | None = None


def client() -> Anthropic:
    global _client
    if _client is None:
        if not config.ANTHROPIC_API_KEY:
            raise RuntimeError("ANTHROPIC_API_KEY not set.")
        # max_retries handles transient network/TLS hiccups (e.g. bad-record-mac
        # mid-connection). SDK default is 2; bump so a flaky moment doesn't surface
        # as a fallback message.
        _client = Anthropic(api_key=config.ANTHROPIC_API_KEY, max_retries=4)
    return _client


def read(
    user_message: str,
    runtime: RuntimeContext,
    *,
    deep: bool = False,
    max_tokens: int | None = None,
    subject_id: int | None = None,
    slack_channel_id: str | None = None,
    slack_thread_ts: str | None = None,
    slack_message_ts: str | None = None,
) -> str:
    """Get a reading from ora. Logs the exchange to the readings table."""
    model = config.MODEL_DEEP if deep else config.MODEL_DEFAULT
    # Caps that match the per-surface instructions in RuntimeContext. Backstop only —
    # the response-shape instruction in the runtime context does the real steering.
    if max_tokens is None:
        max_tokens = 600 if deep else 200

    system_blocks = [
        {
            "type": "text",
            "text": stable_system_prompt(),
            "cache_control": {"type": "ephemeral"},
        },
        {
            "type": "text",
            "text": runtime.render(),
        },
    ]

    response = client().messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system_blocks,
        messages=[{"role": "user", "content": user_message}],
    )

    text = "".join(block.text for block in response.content if block.type == "text").strip()

    _log_reading(
        subject_id=subject_id,
        surface=runtime.surface,
        slack_channel_id=slack_channel_id,
        slack_thread_ts=slack_thread_ts,
        slack_message_ts=slack_message_ts,
        question=user_message,
        response=text,
        model=model,
    )

    return text


def _log_reading(**fields) -> None:
    try:
        with db.cursor() as cur:
            cur.execute(
                """
                INSERT INTO readings
                  (subject_id, surface, slack_channel_id, slack_thread_ts,
                   slack_message_ts, question, response, model)
                VALUES
                  (:subject_id, :surface, :slack_channel_id, :slack_thread_ts,
                   :slack_message_ts, :question, :response, :model)
                """,
                fields,
            )
    except Exception:
        logger.exception("failed to log reading; continuing")
