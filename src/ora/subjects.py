"""Subjects (people + entities like clone). DB CRUD and chart loading."""

import json
import logging
from dataclasses import asdict
from functools import lru_cache

import yaml

from ora import config, db
from ora.charts import render, saju, western

logger = logging.getLogger(__name__)


def load_clone_from_yaml() -> int:
    """Load data/clone.yaml into subjects + compute & store charts. Returns subject id."""
    data = yaml.safe_load(config.CLONE_YAML_PATH.read_text(encoding="utf-8"))
    return upsert_with_charts(
        kind=data["kind"],
        slack_user_id=data.get("slack_user_id"),
        display_name=data["display_name"],
        birth_date=data["birth_date"],
        birth_time=data.get("birth_time"),
        birth_tz=data["birth_tz"],
        birth_place=data["birth_place"],
        birth_lat=data.get("birth_lat"),
        birth_lon=data.get("birth_lon"),
        notes=data.get("notes"),
    )


def upsert_with_charts(
    *,
    kind: str,
    slack_user_id: str | None,
    display_name: str,
    birth_date: str,
    birth_time: str | None,
    birth_tz: str,
    birth_place: str,
    birth_lat: float | None,
    birth_lon: float | None,
    notes: str | None,
) -> int:
    """Insert/update a subject and (re)compute their saju + western chart."""
    with db.cursor() as cur:
        existing = None
        if slack_user_id:
            cur.execute("SELECT id FROM subjects WHERE slack_user_id = ?", (slack_user_id,))
            row = cur.fetchone()
            existing = row["id"] if row else None
        else:
            cur.execute(
                "SELECT id FROM subjects WHERE kind = ? AND display_name = ? AND slack_user_id IS NULL",
                (kind, display_name),
            )
            row = cur.fetchone()
            existing = row["id"] if row else None

        if existing:
            cur.execute(
                """
                UPDATE subjects SET
                  birth_date=?, birth_time=?, birth_tz=?, birth_place=?,
                  birth_lat=?, birth_lon=?, notes=?, updated_at=datetime('now')
                WHERE id=?
                """,
                (birth_date, birth_time, birth_tz, birth_place,
                 birth_lat, birth_lon, notes, existing),
            )
            subject_id = existing
        else:
            cur.execute(
                """
                INSERT INTO subjects
                  (kind, slack_user_id, display_name, birth_date, birth_time,
                   birth_tz, birth_place, birth_lat, birth_lon, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (kind, slack_user_id, display_name, birth_date, birth_time,
                 birth_tz, birth_place, birth_lat, birth_lon, notes),
            )
            subject_id = cur.lastrowid

    _compute_and_store_saju(subject_id, birth_date, birth_time, birth_tz)
    if birth_lat is not None and birth_lon is not None:
        _compute_and_store_western(
            subject_id, birth_date, birth_time, birth_tz,
            birth_lat, birth_lon, display_name, birth_place,
        )

    _clear_cached_renders()
    return subject_id


def _compute_and_store_saju(subject_id: int, birth_date, birth_time, birth_tz) -> None:
    try:
        s = saju.compute(birth_date, birth_time, birth_tz)
    except Exception:
        logger.exception("saju computation failed for subject %s", subject_id)
        return
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO saju_pillars
              (subject_id, year_pillar, month_pillar, day_pillar, hour_pillar,
               day_master, elements_json, computed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(subject_id) DO UPDATE SET
              year_pillar=excluded.year_pillar,
              month_pillar=excluded.month_pillar,
              day_pillar=excluded.day_pillar,
              hour_pillar=excluded.hour_pillar,
              day_master=excluded.day_master,
              elements_json=excluded.elements_json,
              computed_at=datetime('now')
            """,
            (subject_id, s.year, s.month, s.day, s.hour, s.day_master,
             json.dumps(s.elements, ensure_ascii=False)),
        )


def _compute_and_store_western(
    subject_id, birth_date, birth_time, birth_tz, birth_lat, birth_lon,
    name, city,
):
    try:
        c = western.compute(
            birth_date, birth_time, birth_tz, birth_lat, birth_lon,
            name=name, city=city,
        )
    except Exception:
        logger.exception("western chart computation failed for subject %s", subject_id)
        return
    placements_json = json.dumps([asdict(p) for p in c.placements], ensure_ascii=False)
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO natal_chart
              (subject_id, placements_json, ascendant, house_system, computed_at)
            VALUES (?, ?, ?, ?, datetime('now'))
            ON CONFLICT(subject_id) DO UPDATE SET
              placements_json=excluded.placements_json,
              ascendant=excluded.ascendant,
              house_system=excluded.house_system,
              computed_at=datetime('now')
            """,
            (subject_id, placements_json, c.ascendant, c.house_system),
        )


def get_by_slack_id(slack_user_id: str) -> dict | None:
    with db.cursor() as cur:
        cur.execute("SELECT * FROM subjects WHERE slack_user_id = ?", (slack_user_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def _load_subject_with_charts(subject_id: int) -> dict | None:
    with db.cursor() as cur:
        cur.execute("SELECT * FROM subjects WHERE id=?", (subject_id,))
        s = cur.fetchone()
        if not s:
            return None
        cur.execute("SELECT * FROM saju_pillars WHERE subject_id=?", (subject_id,))
        sp = cur.fetchone()
        cur.execute("SELECT * FROM natal_chart WHERE subject_id=?", (subject_id,))
        nc = cur.fetchone()
    return {"subject": dict(s), "saju": dict(sp) if sp else None, "natal": dict(nc) if nc else None}


def render_subject_markdown(subject_id: int) -> str:
    bundle = _load_subject_with_charts(subject_id)
    if not bundle:
        return "(subject not found)"
    s = bundle["subject"]

    saju_obj = None
    if bundle["saju"]:
        sp = bundle["saju"]
        saju_obj = saju.SajuPillars(
            year=sp["year_pillar"],
            month=sp["month_pillar"],
            day=sp["day_pillar"],
            hour=sp["hour_pillar"],
            day_master=sp["day_master"],
            elements=json.loads(sp["elements_json"]) if sp["elements_json"] else {},
        )

    natal_obj = None
    if bundle["natal"]:
        nc = bundle["natal"]
        placements = [
            western.Placement(**p) for p in json.loads(nc["placements_json"] or "[]")
        ]
        natal_obj = western.NatalChart(
            placements=placements,
            ascendant=nc["ascendant"],
            moon_approximate=s["birth_time"] is None,
            house_system=nc["house_system"] or "whole_sign",
        )

    return render.render_subject(
        display_name=s["display_name"],
        birth_date=s["birth_date"],
        birth_time=s["birth_time"],
        birth_place=s["birth_place"],
        saju=saju_obj,
        western=natal_obj,
    )


@lru_cache(maxsize=1)
def get_clone_id() -> int:
    """Return clone's subject id, loading from yaml if not yet in DB."""
    with db.cursor() as cur:
        cur.execute(
            "SELECT id FROM subjects WHERE kind='entity' AND display_name='clone' AND slack_user_id IS NULL"
        )
        row = cur.fetchone()
        if row:
            return row["id"]
    return load_clone_from_yaml()


@lru_cache(maxsize=1)
def clone_chart_markdown() -> str:
    return render_subject_markdown(get_clone_id())


def _clear_cached_renders() -> None:
    clone_chart_markdown.cache_clear()
    get_clone_id.cache_clear()
