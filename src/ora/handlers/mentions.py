"""@ora mentions in any channel."""

import logging
import re

from ora import reading

logger = logging.getLogger(__name__)

MENTION_RE = re.compile(r"<@[A-Z0-9]+>\s*")


def _strip_mentions(text: str) -> str:
    return MENTION_RE.sub("", text).strip()


def _display_name(client, user_id: str) -> str | None:
    try:
        info = client.users_info(user=user_id)
        u = info.get("user", {})
        profile = u.get("profile", {})
        return profile.get("display_name") or profile.get("real_name") or u.get("name")
    except Exception:
        logger.exception("users_info failed for %s", user_id)
        return None


def handle_app_mention(event, say, client):
    user_id = event.get("user")
    raw_text = event.get("text", "")
    question = _strip_mentions(raw_text)
    channel_id = event.get("channel")
    thread_ts = event.get("thread_ts") or event["ts"]
    is_in_thread = bool(event.get("thread_ts"))

    logger.info("app_mention from %s in %s: %s", user_id, channel_id, question)

    response = reading.respond(
        question or "(no question — give a brief opening or invite one)",
        surface="thread_reply" if is_in_thread else "channel_mention",
        slack_user_id=user_id,
        user_display_name=_display_name(client, user_id) if user_id else None,
        slack_channel_id=channel_id,
        slack_thread_ts=thread_ts,
        slack_message_ts=event.get("ts"),
    )

    say(text=response, thread_ts=thread_ts)
