"""/ora slash command.

Subcommands:
  /ora              → same as /ora today
  /ora today        → today's 일진 + brief read against clone
  /ora me           → reading on the asker's chart (must have one on file)
  /ora setup        → open birth-data modal
  /ora memory       → show what ora remembers about you
  /ora forget       → wipe what ora remembers about you
"""

import logging

from ora import memory, reading, subjects
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

    if text in ("memory", "remember", "what do you know about me"):
        row = subjects.get_by_slack_id(user_id)
        if not row:
            respond(
                response_type="ephemeral",
                text="No chart on file, so no memory either. `/ora setup` if you want in.",
            )
            return
        digest = memory.get_digest(row["id"])
        if not digest:
            respond(
                response_type="ephemeral",
                text="Nothing on you yet — we haven't talked enough. Ask me something.",
            )
            return
        respond(
            response_type="ephemeral",
            text=f"Here's what I've got on you (private, just for me):\n\n{digest}",
        )
        return

    if text in ("forget", "forget me"):
        row = subjects.get_by_slack_id(user_id)
        if not row:
            respond(
                response_type="ephemeral",
                text="Nothing to forget — no chart on file.",
            )
            return
        removed = memory.forget(row["id"])
        respond(
            response_type="ephemeral",
            text="Wiped. Clean slate." if removed
                 else "Nothing was on file to wipe. Already clean.",
        )
        return

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
