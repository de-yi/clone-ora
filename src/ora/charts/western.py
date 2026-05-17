"""Western natal chart computation via kerykeion (Swiss Ephemeris underneath).

Convention:
  - If `birth_time` is None, compute a "solar chart": noon local time, all
    planetary signs valid, Moon flagged approximate (it moves ~13°/day so
    up to ±6.5° drift), Ascendant/houses omitted.
"""

from dataclasses import dataclass, field

# Planets we care about for a standard reading. kerykeion exposes more
# (true_node, mean_node, lilith, chiron) — add later if useful.
PLANETS = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn",
           "uranus", "neptune", "pluto"]


@dataclass
class Placement:
    name: str           # 'sun', 'moon', ...
    sign: str           # 'Pisces', etc.
    degree: float       # 0–30 within the sign
    house: int | None   # 1–12, or None for solar chart


@dataclass
class NatalChart:
    placements: list[Placement] = field(default_factory=list)
    ascendant: str | None = None        # sign on the Ascendant; None for solar chart
    moon_approximate: bool = False      # True for solar chart
    house_system: str = "whole_sign"

    def by_name(self, name: str) -> Placement | None:
        for p in self.placements:
            if p.name == name:
                return p
        return None


def compute(
    birth_date: str,
    birth_time: str | None,
    birth_tz: str,
    birth_lat: float,
    birth_lon: float,
    *,
    name: str = "subject",
    city: str = "Unknown",
    nation: str = "",
) -> NatalChart:
    """Compute a natal chart.

    birth_date: 'YYYY-MM-DD', birth_time: 'HH:MM' or None.
    """
    from kerykeion import AstrologicalSubject

    y, m, d = (int(x) for x in birth_date.split("-"))
    if birth_time:
        hh, mm = (int(x) for x in birth_time.split(":"))
        time_known = True
    else:
        hh, mm = 12, 0
        time_known = False

    subject = AstrologicalSubject(
        name=name,
        year=y, month=m, day=d,
        hour=hh, minute=mm,
        city=city,
        nation=nation,
        lat=birth_lat, lng=birth_lon,
        tz_str=birth_tz,
        houses_system_identifier="W",  # whole-sign houses (Hellenistic default)
        online=False,                  # we provide lat/lng/tz_str ourselves
    )

    placements: list[Placement] = []
    for planet_name in PLANETS:
        p = getattr(subject, planet_name, None)
        if p is None:
            continue
        # kerykeion's planet objects expose: .sign, .position (deg in sign), .house
        sign = getattr(p, "sign", None)
        position = getattr(p, "position", None)
        house = getattr(p, "house", None)  # e.g. 'First_House' or similar
        house_num = _house_to_int(house) if time_known else None
        placements.append(Placement(
            name=planet_name,
            sign=str(sign) if sign is not None else "",
            degree=float(position) if position is not None else 0.0,
            house=house_num,
        ))

    ascendant = None
    if time_known:
        asc = getattr(subject, "first_house", None)
        ascendant = str(getattr(asc, "sign", None)) if asc is not None else None

    return NatalChart(
        placements=placements,
        ascendant=ascendant,
        moon_approximate=not time_known,
        house_system="whole_sign",
    )


def _house_to_int(house) -> int | None:
    """kerykeion exposes house as 'First_House'…'Twelfth_House' or an int.

    Be defensive about either form.
    """
    if house is None:
        return None
    if isinstance(house, int):
        return house
    mapping = {
        "First_House": 1, "Second_House": 2, "Third_House": 3, "Fourth_House": 4,
        "Fifth_House": 5, "Sixth_House": 6, "Seventh_House": 7, "Eighth_House": 8,
        "Ninth_House": 9, "Tenth_House": 10, "Eleventh_House": 11, "Twelfth_House": 12,
    }
    return mapping.get(str(house))
