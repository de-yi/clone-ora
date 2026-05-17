"""1:1 DMs with ora."""

import logging

from ora import reading

logger = logging.getLogger(__name__)


def _display_name(client, user_id: str) -> str | None:
    try:
        info = client.users_info(user=user_id)
        u = info.get("user", {})
        profile = u.get("profile", {})
        return profile.get("display_name") or profile.get("real_name") or u.get("name")
    except Exception:
        logger.exception("users_info failed for %s", user_id)
        return None


def handle_message(event, say, client):
    """Triggered for every message event. Handle DMs; pass on everything else."""
    if event.get("channel_type") != "im":
        return
    if event.get("bot_id") or event.get("subtype") == "bot_message":
        return

    user_id = event.get("user")
    text = (event.get("text") or "").strip()
    channel_id = event.get("channel")
    logger.info("dm from %s: %s", user_id, text)

    if not text:
        return

    response = reading.respond(
        text,
        surface="dm",
        slack_user_id=user_id,
        user_display_name=_display_name(client, user_id) if user_id else None,
        slack_channel_id=channel_id,
        slack_message_ts=event.get("ts"),
    )

    say(response)
