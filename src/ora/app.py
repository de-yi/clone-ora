"""ora — Slack bolt entry point, Socket Mode."""

import logging

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from ora import config, db, subjects
from ora.handlers import commands, daily, dms, huddle, mentions, setup_modal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger("ora")


def build_app() -> App:
    if not config.SLACK_BOT_TOKEN:
        raise RuntimeError("SLACK_BOT_TOKEN not set. Copy .env.example to .env and fill it in.")

    app = App(token=config.SLACK_BOT_TOKEN)

    app.event("app_mention")(mentions.handle_app_mention)
    app.event("message")(dms.handle_message)
    app.event("user_huddle_changed")(huddle.handle_huddle_changed)
    app.command("/ora")(commands.handle_ora_command)
    app.view(setup_modal.CALLBACK_ID)(setup_modal.handle_submission)

    return app


def main() -> None:
    if not config.SLACK_APP_TOKEN:
        raise RuntimeError("SLACK_APP_TOKEN not set (needed for Socket Mode).")

    # Idempotent: CREATE TABLE IF NOT EXISTS + upsert-by-key. Safe every boot.
    logger.info("DB: ensuring schema at %s", config.DB_PATH)
    db.init_schema()
    logger.info("DB: ensuring clone is loaded (computes chart on first run)…")
    subjects.get_clone_id()

    app = build_app()

    if config.ORA_CHANNEL_ID:
        daily.start_scheduler(app.client)
    else:
        logger.warning(
            "ORA_CHANNEL_ID not set — skipping daily-fortune scheduler. "
            "Set it in .env to enable daily posts."
        )

    logger.info("ora starting (Socket Mode)…")
    SocketModeHandler(app, config.SLACK_APP_TOKEN).start()


if __name__ == "__main__":
    main()
