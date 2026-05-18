"""Slack thread / DM transcript fetching for runtime context.

Pulls the last N messages from the current conversation and renders them as a
lean one-line-per-message transcript so ora can see what was just said. Never
raises into the caller — any failure returns None and the reading still goes
out without recent-conversation context.
"""

import logging
import re
from functools import lru_cache

logger = logging.getLogger(__name__)

_MENTION_RE = re.compile(r"<@([A-Z0-9]+)>")
_CHANNEL_LINK_RE = re.compile(r"<#[A-Z0-9]+\|([^>]+)>")
_URL_LINK_RE = re.compile(r"<(https?://[^|>]+)(?:\|[^>]+)?>")


@lru_cache(maxsize=1)
def _bot_user_id(client) -> str | None:
    """Identify our own bot user so we can render ora's own messages as 'ora:'.

    Cached for the process lifetime — the bot user id is stable per token.
    """
    try:
        return client.auth_test().get("user_id")
    except Exception:
        logger.exception("auth_test failed; ora's own messages will fall back to display-name lookup")
        return None


@lru_cache(maxsize=256)
def _display_name(client, user_id: str) -> str:
    """Look up a user's display name, fall back to user id on failure.

    Cached per-process — chat participants are stable; one lookup per unique
    user is enough.
    """
    try:
        info = client.users_info(user=user_id)
        u = info.get("user") or {}
        profile = u.get("profile") or {}
        return (
            profile.get("display_name")
            or profile.get("real_name")
            or u.get("name")
            or user_id
        )
    except Exception:
        logger.exception("users_info failed for %s", user_id)
        return user_id


def _clean(text: str, client) -> str:
    """Replace Slack link/mention syntax with plain-text equivalents."""
    text = _MENTION_RE.sub(lambda m: "@" + _display_name(client, m.group(1)), text)
    text = _CHANNEL_LINK_RE.sub(lambda m: "#" + m.group(1), text)
    text = _URL_LINK_RE.sub(lambda m: m.group(1), text)
    return text.strip()


def _speaker(client, msg: dict) -> str:
    bot_id = _bot_user_id(client)
    user_id = msg.get("user")
    if user_id and bot_id and user_id == bot_id:
        return "ora"
    if user_id:
        return _display_name(client, user_id)
    if msg.get("bot_id"):
        return msg.get("username") or "bot"
    return "unknown"


def _format_transcript(client, messages: list[dict]) -> str:
    lines = []
    for msg in messages:
        if msg.get("subtype") in ("channel_join", "channel_leave"):
            continue
        text = _clean(msg.get("text") or "", client)
        if not text:
            continue
        lines.append(f"{_speaker(client, msg)}: {text}")
    return "\n".join(lines)


def fetch_thread_context(
    client,
    *,
    channel_id: str,
    thread_ts: str | None,
    surface: str,
    current_message_ts: str | None,
    thread_limit: int,
    dm_limit: int,
) -> str | None:
    """Return a formatted transcript of the recent conversation, or None.

    Routing:
    - thread_reply / huddle_thread → conversations.replies on thread_ts
    - dm with thread_ts            → conversations.replies on thread_ts
    - dm without thread_ts         → conversations.history on the DM channel
    - channel_mention / daily_post → None (fresh thread, no prior context)
    """
    if not channel_id:
        return None

    try:
        if surface in ("thread_reply", "huddle_thread") and thread_ts:
            resp = client.conversations_replies(
                channel=channel_id, ts=thread_ts, limit=thread_limit, inclusive=True
            )
            messages = resp.get("messages") or []
        elif surface == "dm":
            if thread_ts:
                resp = client.conversations_replies(
                    channel=channel_id, ts=thread_ts, limit=dm_limit, inclusive=True
                )
                messages = resp.get("messages") or []
            else:
                resp = client.conversations_history(
                    channel=channel_id, limit=dm_limit, inclusive=True
                )
                # history returns newest-first; flip so the transcript reads top-down.
                messages = list(reversed(resp.get("messages") or []))
        else:
            return None
    except Exception:
        logger.exception("slack history fetch failed for channel=%s ts=%s", channel_id, thread_ts)
        return None

    if current_message_ts:
        messages = [m for m in messages if m.get("ts") != current_message_ts]

    if not messages:
        return None

    transcript = _format_transcript(client, messages)
    return transcript or None
