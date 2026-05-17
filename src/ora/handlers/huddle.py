"""Huddle hook — drop a contextual note in the huddle thread when one starts in #ora.

NOTE on the event: Slack fires `user_huddle_changed` when a user's huddle state
changes (they joined or left a huddle). That event tells us *which user* but not
directly which channel's huddle. To map huddle → channel we also need the
huddle's associated thread/channel context, which lives on the channel's
`huddle` object (or the auto-created huddle thread).

For v0 we stub the handler and document the lookup. Real wiring will need to:
  - confirm the huddle is in ORA_CHANNEL_ID (clone's #ora channel)
  - find the huddle thread (conversations.info or message search)
  - post once per huddle, not once per joining user
"""

import logging

from ora import config

logger = logging.getLogger(__name__)


def handle_huddle_changed(event, client):
    """Triggered when a user joins or leaves a huddle.

    TODO:
      - dedupe per huddle (track active huddles in memory or DB)
      - confirm the huddle is in ORA_CHANNEL_ID
      - find the huddle thread_ts
      - assemble RuntimeContext (surface='huddle_thread')
      - call llm.read() with a short-form prompt
      - post in-thread (one or two lines max)
    """
    user = event.get("user", {}).get("id") if isinstance(event.get("user"), dict) else event.get("user")
    logger.info("user_huddle_changed: user=%s channel=%s", user, config.ORA_CHANNEL_ID)
    # Stub: do nothing until we wire the lookup.
