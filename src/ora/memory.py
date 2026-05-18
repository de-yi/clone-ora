"""Per-subject digested memory.

ora keeps a small private note about each subject — recurring themes, life
context they've shared, style preferences. It's rebuilt asynchronously after
readings by a cheap Haiku call so the user-facing reply isn't slowed.

The note is reference material for ora, never shown to the asker. The persona
instruction injected alongside it says "draw on this sparingly — don't recite."
"""

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from ora import config, db, llm

logger = logging.getLogger(__name__)


_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ora-digest")


DIGEST_SYSTEM_PROMPT = """You are maintaining a tiny private memory note that ora (a Slack-bot \
astrologer) keeps about a specific person. The note is for ora's own reference \
and is never shown to the asker.

Rewrite the note to reflect the recent readings. Keep it under 200 words. Plain \
prose, no headers, no bullet padding.

Capture:
- recurring themes / topics this person keeps asking about
- notable life context they've shared (job change, relationship arc, big move, etc.)
- style preferences (wants short answers, likes deep dives, prefers Korean glosses, etc.)

Do NOT track:
- open threads, follow-ups, or to-dos
- specific predictions you made
- anything that would feel surveillance-y if recited back

If a previous note is provided, refine it — keep what still matters, drop what \
went stale, add what's new. Don't grow the note forever; prune aggressively. \
Return only the new note, no preamble."""


def get_digest(subject_id: int | None) -> str | None:
    """Read a subject's digest. Returns None for unknown subject, missing row, or DB error."""
    if subject_id is None:
        return None
    try:
        with db.cursor() as cur:
            cur.execute(
                "SELECT digest FROM subject_memory WHERE subject_id=?", (subject_id,)
            )
            row = cur.fetchone()
            return row["digest"] if row else None
    except Exception:
        logger.exception("get_digest failed for subject_id=%s", subject_id)
        return None


def schedule_update(subject_id: int | None) -> None:
    """Queue an async digest rewrite for this subject. No-op if subject is unknown."""
    if subject_id is None:
        return
    try:
        _executor.submit(update_digest, subject_id)
    except Exception:
        logger.exception("failed to schedule digest update for subject_id=%s", subject_id)


def update_digest(subject_id: int) -> None:
    """Synchronous digest rebuild. Designed to be called from the background executor.

    Debounces if a digest was written within MEMORY_DEBOUNCE_SECONDS. Never raises.
    """
    try:
        _update_digest_inner(subject_id)
    except Exception:
        logger.exception("digest update failed for subject_id=%s", subject_id)


def _update_digest_inner(subject_id: int) -> None:
    with db.cursor() as cur:
        cur.execute(
            "SELECT digest, generation, updated_at FROM subject_memory WHERE subject_id=?",
            (subject_id,),
        )
        existing = cur.fetchone()

        if existing and _within_debounce(existing["updated_at"]):
            logger.debug("digest debounced for subject_id=%s", subject_id)
            return

        cur.execute(
            "SELECT display_name FROM subjects WHERE id=?", (subject_id,)
        )
        subj = cur.fetchone()
        display_name = subj["display_name"] if subj else f"subject {subject_id}"

        cur.execute(
            """
            SELECT id, created_at, surface, question, response
            FROM readings
            WHERE subject_id=?
            ORDER BY id DESC
            LIMIT ?
            """,
            (subject_id, config.MEMORY_READINGS_WINDOW),
        )
        readings = cur.fetchall()

    if len(readings) < 2:
        logger.debug("not enough readings to digest for subject_id=%s", subject_id)
        return

    previous = existing["digest"] if existing else None
    last_reading_id = readings[0]["id"]

    # Readings come newest-first; flip so the model reads chronologically.
    chronological = list(reversed(readings))
    formatted = "\n".join(
        f"[{r['created_at']} {r['surface']}] "
        f"Q: {(r['question'] or '').strip()[:300]} | "
        f"A: {(r['response'] or '').strip()[:400]}"
        for r in chronological
    )

    user_message = (
        f"Subject: {display_name}\n\n"
        f"Previous note:\n{previous or '(none yet)'}\n\n"
        f"Recent readings (chronological):\n{formatted}\n\n"
        "Return the rewritten note."
    )

    response = llm.client().messages.create(
        model=config.MODEL_DIGEST,
        max_tokens=400,
        system=DIGEST_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )
    new_digest = "".join(
        block.text for block in response.content if block.type == "text"
    ).strip()

    if not new_digest:
        logger.warning("digest model returned empty text for subject_id=%s", subject_id)
        return

    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO subject_memory (subject_id, digest, generation, last_reading_id, model)
            VALUES (?, ?, 1, ?, ?)
            ON CONFLICT(subject_id) DO UPDATE SET
                digest          = excluded.digest,
                generation      = subject_memory.generation + 1,
                last_reading_id = excluded.last_reading_id,
                model           = excluded.model,
                updated_at      = datetime('now')
            """,
            (subject_id, new_digest, last_reading_id, config.MODEL_DIGEST),
        )

    logger.info("digest updated for subject_id=%s (%d chars)", subject_id, len(new_digest))


def _within_debounce(updated_at_str: str) -> bool:
    """True if updated_at is within MEMORY_DEBOUNCE_SECONDS of now.

    Stored timestamps are SQLite `datetime('now')` UTC strings (no tz suffix).
    """
    try:
        ts = datetime.fromisoformat(updated_at_str).replace(tzinfo=timezone.utc)
    except ValueError:
        return False
    return datetime.now(timezone.utc) - ts < timedelta(seconds=config.MEMORY_DEBOUNCE_SECONDS)
