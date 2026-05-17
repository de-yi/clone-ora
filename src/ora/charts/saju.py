"""사주 (Korean four pillars) computation via lunar-python.

lunar-python (port of 6tail/lunar-java) handles the lunar calendar,
solar terms (절기), and sexagenary-cycle day computation for us — no
ephemeris maintenance on our end.

Convention:
  - If `birth_time` is None, we compute year/month/day pillars using noon
    local time (gives correct day pillar in all but pathological boundary
    cases) and set hour=None. We do NOT fake an hour pillar.
"""

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

# Korean readings for 천간 (heavenly stems) and 지지 (earthly branches)
STEM_KO = {
    "甲": "갑", "乙": "을", "丙": "병", "丁": "정", "戊": "무",
    "己": "기", "庚": "경", "辛": "신", "壬": "임", "癸": "계",
}
BRANCH_KO = {
    "子": "자", "丑": "축", "寅": "인", "卯": "묘", "辰": "진", "巳": "사",
    "午": "오", "未": "미", "申": "신", "酉": "유", "戌": "술", "亥": "해",
}
STEM_ELEMENT = {
    "甲": "木", "乙": "木", "丙": "火", "丁": "火",
    "戊": "土", "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水",
}
BRANCH_ELEMENT = {
    "子": "水", "丑": "土", "寅": "木", "卯": "木", "辰": "土", "巳": "火",
    "午": "火", "未": "土", "申": "金", "酉": "金", "戌": "土", "亥": "水",
}
ELEMENT_KO = {"木": "목", "火": "화", "土": "토", "金": "금", "水": "수"}


@dataclass
class SajuPillars:
    year: str
    month: str
    day: str
    hour: str | None
    day_master: str             # 일간, just the stem
    elements: dict[str, int]    # 오행 counts across present pillars (Chinese keys)

    def pillar_with_ko(self, pillar: str) -> str:
        """e.g. '丙午' -> '丙午 (병오)'"""
        if not pillar or len(pillar) < 2:
            return pillar or ""
        ko = STEM_KO.get(pillar[0], "?") + BRANCH_KO.get(pillar[1], "?")
        return f"{pillar} ({ko})"


def compute(
    birth_date: str,
    birth_time: str | None,
    birth_tz: str,
) -> SajuPillars:
    """Compute four pillars for the given birth moment.

    birth_date: 'YYYY-MM-DD'
    birth_time: 'HH:MM' or None
    birth_tz:   IANA tz name, e.g. 'Asia/Seoul'
    """
    from lunar_python import Solar  # imported here so the module loads without the dep

    y, m, d = (int(x) for x in birth_date.split("-"))
    if birth_time:
        hh, mm = (int(x) for x in birth_time.split(":"))
        hour_known = True
    else:
        hh, mm = 12, 0
        hour_known = False

    # Note: lunar-python's Solar uses naive local time of the birth place.
    # We trust the user's birth_tz to mean "civil local time at that tz".
    # ZoneInfo isn't strictly needed for the calc, but we resolve it to
    # surface bad tz strings early.
    ZoneInfo(birth_tz)

    solar = Solar.fromYmdHms(y, m, d, hh, mm, 0)
    ec = solar.getLunar().getEightChar()

    year_p = ec.getYear()
    month_p = ec.getMonth()
    day_p = ec.getDay()
    hour_p = ec.getTime() if hour_known else None
    day_master = day_p[0]

    pillars_present = [year_p, month_p, day_p] + ([hour_p] if hour_p else [])
    elements: dict[str, int] = {"木": 0, "火": 0, "土": 0, "金": 0, "水": 0}
    for p in pillars_present:
        elements[STEM_ELEMENT[p[0]]] += 1
        elements[BRANCH_ELEMENT[p[1]]] += 1

    return SajuPillars(
        year=year_p,
        month=month_p,
        day=day_p,
        hour=hour_p,
        day_master=day_master,
        elements=elements,
    )


def day_pillar_for(dt: datetime) -> str:
    """일진 — the day pillar for a given calendar date. Used for daily fortune."""
    from lunar_python import Solar

    solar = Solar.fromYmdHms(dt.year, dt.month, dt.day, 12, 0, 0)
    return solar.getLunar().getEightChar().getDay()
