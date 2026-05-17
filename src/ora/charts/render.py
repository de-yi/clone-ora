"""Render chart data as markdown for inclusion in the LLM runtime context.

Two kinds of renders:
  - render_subject: subject + saju + western chart (the static portrait)
  - render_today:   today's 일진 + brief notable transits to the subject

Keep these terse — they're for the model to *use*, not for the user to read.
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from ora.charts.saju import (
    BRANCH_ELEMENT,
    BRANCH_KO,
    ELEMENT_KO,
    SajuPillars,
    STEM_ELEMENT,
    STEM_KO,
    day_pillar_for,
)
from ora.charts.western import NatalChart


def _ko(pillar: str) -> str:
    if not pillar or len(pillar) < 2:
        return pillar or ""
    return f"{pillar} ({STEM_KO.get(pillar[0], '?')}{BRANCH_KO.get(pillar[1], '?')})"


def render_saju(s: SajuPillars) -> str:
    elements_line = " · ".join(
        f"{el}({ELEMENT_KO[el]}) {s.elements[el]}"
        for el in ("木", "火", "土", "金", "水")
    )
    return (
        f"사주 four pillars:\n"
        f"- 年柱 (year):  {_ko(s.year)}\n"
        f"- 月柱 (month): {_ko(s.month)}\n"
        f"- 日柱 (day):   {_ko(s.day)} — 일간 {s.day_master} ({STEM_KO.get(s.day_master, '?')}, "
        f"{ELEMENT_KO[STEM_ELEMENT[s.day_master]]})\n"
        f"- 時柱 (hour):  {_ko(s.hour) if s.hour else 'unknown (omitted)'}\n"
        f"오행 balance: {elements_line}"
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
        f"**{display_name}** — born {birth_date}"
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
    """일진 for the given day. Western transits TODO — keep short for now."""
    dt = datetime.combine(when, datetime.min.time(), tzinfo=ZoneInfo(tz))
    today_pillar = day_pillar_for(dt)
    return (
        f"Today ({when.isoformat()}, {tz}):\n"
        f"- 일진 (day pillar): {_ko(today_pillar)} — "
        f"stem element {ELEMENT_KO[STEM_ELEMENT[today_pillar[0]]]}, "
        f"branch element {ELEMENT_KO[BRANCH_ELEMENT[today_pillar[1]]]}\n"
        f"- Western transits: (not yet computed — TODO)"
    )
