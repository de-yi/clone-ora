# ora

ora is a believer-practitioner AI persona doing 사주 (Korean four pillars) and Western astrology for **clone**, accessible through Slack.

She has a chart for clone itself, posts a daily reading in `#ora`, answers follow-ups in thread, and runs personal readings in DM for members who've shared their birth data.

Voice and character live in [`PERSONA.md`](PERSONA.md). Source canon (classical 명리학 texts, Hellenistic and modern Western references) lives in [`REFERENCE.md`](REFERENCE.md).

## Status

v0 scaffold. Persona + canon are written. Slack handlers are stubs. Chart computation modules are stubs. Real wiring lands incrementally.

## Architecture

```
PERSONA.md / REFERENCE.md   ← persona + source canon (system-prompt material)
data/clone.yaml             ← clone-the-company as a chart subject
src/ora/
  app.py                    ← entry point, Slack bolt app, Socket Mode
  config.py                 ← env vars
  db.py                     ← SQLite (subjects, saju_pillars, natal_chart, readings, subject_memory)
  persona.py                ← assembles system prompt with runtime context
  llm.py                    ← Anthropic client (Sonnet 4.6 default, Opus 4.7 for deep)
  slack_history.py          ← pulls recent thread/DM messages for runtime context
  memory.py                 ← per-subject digested memory (async Haiku rewrites)
  handlers/
    mentions.py             ← @ora in channel
    dms.py                  ← 1:1 DMs
    huddle.py               ← huddle started → contextual thread post
    commands.py             ← /ora slash command (incl. /ora setup modal)
    daily.py                ← APScheduler cron for daily fortune
  charts/
    saju.py                 ← lunar-python wrapper, 사주 computation
    western.py              ← kerykeion wrapper, natal chart computation
schema.sql                  ← SQLite schema
manifest.yaml               ← Slack app manifest (scopes, events, slash command)
```

## Setup

```bash
# 1. Install deps
uv venv && uv pip install -e .   # or: python -m venv .venv && pip install -e .

# 2. Create the Slack app
#    - Go to api.slack.com/apps → Create New App → From manifest
#    - Paste manifest.yaml
#    - Install to clone workspace
#    - Generate an App-Level Token with `connections:write` (Socket Mode)
#    - Copy the bot token and app token

# 3. Configure
cp .env.example .env
# Fill in SLACK_BOT_TOKEN, SLACK_APP_TOKEN, ANTHROPIC_API_KEY, ORA_CHANNEL_ID

# 4. Init DB + load clone's chart (computes saju + Western placements)
python -m ora.scripts.init

# 5. Run
ora
# or: python -m ora.app
```

## What works / what doesn't (v0)

- [x] Persona and canon written
- [x] Project scaffold, deps pinned
- [x] SQLite schema
- [x] Persona / system-prompt loader with prompt caching
- [x] 사주 computation (`lunar-python`)
- [x] Western natal chart (`kerykeion`)
- [x] Slack handlers: `@ora` mentions, DMs, `/ora today`, `/ora me`, `/ora setup` modal
- [x] Daily fortune cron (APScheduler, idempotent per-day)
- [x] Slack app manifest
- [x] Dockerfile + fly.toml
- [x] Thread/DM continuity (last N messages → context) + per-subject digested memory (`/ora memory`, `/ora forget`)
- [ ] Huddle hook (handler is stubbed; needs huddle → channel mapping)
- [ ] Western transits-to-natal computed properly (today's planet positions vs. subject's natal) — currently only the saju day-pillar appears in the runtime context
- [ ] Geocoding birth place (currently defaults to Seoul coords)

## CLI scripts

```bash
python -m ora.scripts.init    # init DB schema + load clone + compute charts
```

## Deploying to Fly.io

```bash
# one-time setup
fly launch --copy-config --no-deploy            # picks up fly.toml; reuse the existing app name or pick another
fly volumes create ora_data --region nrt --size 1
fly secrets set \
  SLACK_BOT_TOKEN=xoxb-... \
  SLACK_APP_TOKEN=xapp-... \
  ANTHROPIC_API_KEY=sk-ant-... \
  ORA_CHANNEL_ID=C0XXXXXX

# deploy
fly deploy
fly logs        # tail
```

Notes:
- Socket Mode means no inbound HTTP — `fly.toml` deliberately has no `[http_service]`. The bot opens a WebSocket out to Slack.
- The SQLite DB lives on the mounted volume at `/data/ora.db` so restarts don't lose chart data.
- Daily fortune fires at `ORA_DAILY_FORTUNE_HOUR` (default 9) in `ORA_TIMEZONE` (default Asia/Seoul). Override via `fly secrets set` or `[env]` in `fly.toml`.

## Useful Python REPL recipes

```python
from ora import subjects
print(subjects.clone_chart_markdown())   # see clone's chart as the model sees it

# Add a person manually until /ora setup ships:
subjects.upsert_with_charts(
    kind="person",
    slack_user_id="U0123456",
    display_name="daeun",
    birth_date="1995-04-12",
    birth_time="07:30",
    birth_tz="Asia/Seoul",
    birth_place="Seoul, South Korea",
    birth_lat=37.5665, birth_lon=126.9780,
    notes=None,
)
```
