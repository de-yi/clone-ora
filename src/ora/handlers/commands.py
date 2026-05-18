"""/ora slash command.

Subcommands:
  /ora              → same as /ora today
  /ora today        → today's 일진 + brief read against clone
  /ora me           → reading on the asker's chart (must have one on file)
  /ora setup        → open birth-data modal (TODO)
"""

import logging

from ora import reading, subjects
from ora.handlers import setup_modal

logger = logging.getLogger(__name__)


def handle_ora_command(ack, command, client, respond):
    text = (command.get("text") or "").strip().lower()
    user_id = command["user_id"]
    user_name = command.get("user_name")
    logger.info("/ora from %s: %r", user_id, text)

    if text in ("setup", "set", "register"):
        # ack first so Slack sees a fast response, then open modal
        ack()
        try:
            setup_modal.open_modal(client, command["trigger_id"])
        except Exception:
            logger.exception("failed to open setup modal")
            respond(response_type="ephemeral",
                    text="couldn't open the setup form just now. try again in a sec.")
        return

    ack()

    if text == "me":
        row = subjects.get_by_slack_id(user_id)
        if not row:
            respond(
                response_type="ephemeral",
                text="No chart on file for you yet. Use `/ora setup` (when it lands) or DM me your birth date/time/place. — ora",
            )
            return
        response_text = reading.respond(
            "Give me a short reading on my own chart — what's the shape of me, what should I know.",
            surface="dm",
            slack_user_id=user_id,
            user_display_name=user_name,
            slack_client=client,
        )
        respond(response_type="ephemeral", text=response_text)
        return

    # Default: /ora and /ora today both give today's reading against clone
    response_text = reading.respond(
        "Give a short reading on today for clone — the day's energy, what it asks of the company.",
        surface="channel_mention",
        slack_user_id=user_id,
        user_display_name=user_name,
        slack_client=client,
    )
    respond(response_type="ephemeral", text=response_text)
