"""Render chart data as markdown for inclusion in the LLM runtime context.

Two kinds of renders:
  - render_subject: subject + saju + western chart (the static portrait)
  - render_today:   today's day-energy + brief notable transits to the subject

Keep these terse — they're for the model to *use*, not for the user to read.

**English-first formatting.** The persona rule is English-only output with
Korean/Chinese symbols in parens. If we feed the model Chinese-leading data,
it tends to echo the same form back. So every pillar appears here as
"Element Animal (symbols / Korean reading)" — English first.
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from ora.charts.saju import (
    BRANCH_ELEMENT,
    BRANCH_EN,
    BRANCH_KO,
    ELEMENT_EN,
    ELEMENT_KO,
    SajuPillars,
    STEM_ELEMENT,
    STEM_EN,
    STEM_KO,
    day_pillar_for,
)
from ora.charts.western import NatalChart


def _pillar(p: str | None) -> str:
    """Format a pillar in English-first form: 'Yang Water Dragon (壬辰 / 임진)'."""
    if not p or len(p) < 2:
        return "unknown"
    stem, branch = p[0], p[1]
    return (
        f"{STEM_EN.get(stem, stem)} {BRANCH_EN.get(branch, branch)} "
        f"({p} / {STEM_KO.get(stem, '?')}{BRANCH_KO.get(branch, '?')})"
    )


def render_saju(s: SajuPillars) -> str:
    elements_line = " · ".join(
        f"{ELEMENT_EN[el]} {s.elements[el]}"
        for el in ("木", "火", "土", "金", "水")
    )
    day_master_en = STEM_EN.get(s.day_master, s.day_master)
    return (
        "Four pillars (사주):\n"
        f"- Year:  {_pillar(s.year)}\n"
        f"- Month: {_pillar(s.month)}\n"
        f"- Day:   {_pillar(s.day)} — Day Master is {day_master_en} ({s.day_master})\n"
        f"- Hour:  {_pillar(s.hour) if s.hour else 'unknown — no hour pillar'}\n"
        f"Five-element balance: {elements_line}"
    )


def render_western(c: NatalChart) -> str:
    lines = ["Western placements:"]
    for p in c.placements:
        suffix = ""
        if p.name == "moon" and c.moon_approximate:
            suffix = " (approximate — no birth time)"
        house = f", house {p.house}" if p.house else ""
        lines.append(f"- {p.name.capitalize()}: {p.sign} {p.degree:.1f}°{house}{suffix}")
    if c.ascendant:
        lines.append(f"- Ascendant: {c.ascendant}")
    else:
        lines.append("- Ascendant: unavailable (no birth time)")
    return "\n".join(lines)


def render_subject(
    *,
    display_name: str,
    birth_date: str,
    birth_time: str | None,
    birth_place: str,
    saju: SajuPillars | None,
    western: NatalChart | None,
) -> str:
    header = (
        f"{display_name} — born {birth_date}"
        f"{' at ' + birth_time if birth_time else ' (time unknown)'}"
        f", {birth_place}"
    )
    parts = [header]
    if saju:
        parts.append(render_saju(saju))
    if western:
        parts.append(render_western(western))
    return "\n\n".join(parts)


def render_today(when: date, tz: str = "Asia/Seoul") -> str:
    """Today's day-energy. Western transits TODO — keep short for now."""
    dt = datetime.combine(when, datetime.min.time(), tzinfo=ZoneInfo(tz))
    today_pillar = day_pillar_for(dt)
    stem_el = ELEMENT_EN[STEM_ELEMENT[today_pillar[0]]]
    branch_el = ELEMENT_EN[BRANCH_ELEMENT[today_pillar[1]]]
    return (
        f"Today ({when.isoformat()}, {tz}):\n"
        f"- Day energy: {_pillar(today_pillar)} — "
        f"{stem_el} stem on {branch_el} branch\n"
        f"- Western transits: (not yet computed)"
    )
