"""Environment configuration. Load .env once at import."""

import os
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(REPO_ROOT / ".env")


def _required(key: str) -> str:
    value = os.environ.get(key)
    if not value:
        raise RuntimeError(f"Missing required env var: {key}")
    return value


SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

def _resolve_db_path() -> Path:
    raw = os.environ.get("ORA_DB_PATH")
    if not raw:
        return REPO_ROOT / "ora.db"
    p = Path(raw)
    return p if p.is_absolute() else REPO_ROOT / p


DB_PATH = _resolve_db_path()
ORA_CHANNEL_ID = os.environ.get("ORA_CHANNEL_ID", "")
ORA_DAILY_FORTUNE_HOUR = int(os.environ.get("ORA_DAILY_FORTUNE_HOUR", "9"))
ORA_TIMEZONE = os.environ.get("ORA_TIMEZONE", "Asia/Seoul")

MODEL_DEFAULT = os.environ.get("ORA_MODEL_DEFAULT", "claude-sonnet-4-6")
MODEL_DEEP = os.environ.get("ORA_MODEL_DEEP", "claude-opus-4-7")

SCHEMA_PATH = REPO_ROOT / "schema.sql"
PERSONA_PATH = REPO_ROOT / "PERSONA.md"
REFERENCE_PATH = REPO_ROOT / "REFERENCE.md"
CLONE_YAML_PATH = REPO_ROOT / "data" / "clone.yaml"
