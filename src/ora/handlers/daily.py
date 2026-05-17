"""Daily fortune cron — posts clone's reading to #ora every morning.

Runs in a background thread (APScheduler). Idempotent per day: if a daily_post
is already in the readings table for today, the job no-ops. So a mid-day
restart won't double-post.
"""

import logging
from datetime import date, datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler

from ora import config, db, llm, subjects
from ora.charts import render
from ora.persona import RuntimeContext

logger = logging.getLogger(__name__)


def _already_posted(today: date) -> bool:
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT 1 FROM readings
            WHERE surface = 'daily_post'
              AND slack_channel_id = ?
              AND date(created_at) = date(?)
            LIMIT 1
            """,
            (config.ORA_CHANNEL_ID, today.isoformat()),
        )
        return cur.fetchone() is not None


def post_daily_fortune(slack_client) -> None:
    if not config.ORA_CHANNEL_ID:
        logger.warning("ORA_CHANNEL_ID not set; skipping daily fortune")
        return

    today = datetime.now(ZoneInfo(config.ORA_TIMEZONE)).date()

    if _already_posted(today):
        logger.info("daily fortune already posted for %s; skipping", today)
        return

    clone_md = subjects.clone_chart_markdown()
    today_md = render.render_today(today, tz=config.ORA_TIMEZONE)
    runtime = RuntimeContext(
        today=today,
        surface="daily_post",
        clone_chart=f"{clone_md}\n\n{today_md}",
    )

    prompt = (
        f"Write today's daily fortune post for clone. Today is {today.isoformat()}. "
        f"Start with the date marker on its own line ({today.isoformat()} · clone's day), "
        f"then the reading. Plain text. Short."
    )

    try:
        text = llm.read(
            prompt,
            runtime,
            slack_channel_id=config.ORA_CHANNEL_ID,
        )
    except Exception:
        logger.exception("LLM call failed for daily fortune; not posting")
        return

    try:
        slack_client.chat_postMessage(channel=config.ORA_CHANNEL_ID, text=text)
        logger.info("posted daily fortune for %s", today)
    except Exception:
        logger.exception("failed to post daily fortune to %s", config.ORA_CHANNEL_ID)


def start_scheduler(slack_client) -> BackgroundScheduler:
    """Start the daily-fortune cron. Returns the scheduler so caller can keep a ref."""
    scheduler = BackgroundScheduler(timezone=config.ORA_TIMEZONE)
    scheduler.add_job(
        post_daily_fortune,
        trigger="cron",
        hour=config.ORA_DAILY_FORTUNE_HOUR,
        minute=0,
        args=[slack_client],
        id="daily_fortune",
        replace_existing=True,
        misfire_grace_time=3600,  # if the bot was down at fire time, still post within an hour
    )
    scheduler.start()
    logger.info(
        "daily-fortune scheduler started — fires at %02d:00 %s",
        config.ORA_DAILY_FORTUNE_HOUR, config.ORA_TIMEZONE,
    )
    return scheduler
