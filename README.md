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
  db.py                     ← SQLite (subjects, saju_pillars, natal_chart, readings)
  persona.py                ← assembles system prompt with runtime context
  llm.py                    ← Anthropic client (Sonnet 4.6 default, Opus 4.7 for deep)
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
- [x] Persona / system-prompt loader
- [x] Anthropic wrapper with prompt caching (PERSONA + REFERENCE cached)
- [x] 사주 computation (`lunar-python`) — year/month/day pillars + hour if known, 일간, 오행 balance
- [x] Western natal chart (`kerykeion`) — planetary placements; Ascendant + houses when birth time known
- [x] Real Slack handlers: `@ora` mentions, DMs, `/ora today`, `/ora me`
- [x] Slack app manifest
- [ ] `/ora setup` modal (Block Kit) — for now, add users manually via `subjects.upsert_with_charts(...)`
- [ ] Daily fortune cron
- [ ] DM thread continuity (last N messages → context)
- [ ] Huddle hook (handler is stubbed; needs huddle → channel mapping)
- [ ] Western transits to natal (today's chart placements vs. subject's natal)
- [ ] Fly.io / Railway deploy

## CLI scripts

```bash
python -m ora.scripts.init    # init DB schema + load clone + compute charts
```

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
