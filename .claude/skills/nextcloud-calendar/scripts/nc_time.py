"""Pure time handling: parsing of user-facing time expressions and slot arithmetic."""

import re
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

RELATIVE_PATTERN = re.compile(r"^([+-])(\d+)([mhdw])$")
DURATION_PATTERN = re.compile(r"^(?:(\d+)h)?(?:(\d+)m)?$|^(\d+)$")
CLOCK_RANGE_PATTERN = re.compile(r"^(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})$")

WEEKDAY_INDEX = {
    "mon": 0,
    "tue": 1,
    "wed": 2,
    "thu": 3,
    "fri": 4,
    "sat": 5,
    "sun": 6,
}

UNIT_TO_DELTA = {
    "m": lambda n: timedelta(minutes=n),
    "h": lambda n: timedelta(hours=n),
    "d": lambda n: timedelta(days=n),
    "w": lambda n: timedelta(weeks=n),
}

DATETIME_FORMATS = (
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%d.%m.%Y %H:%M",
    "%d.%m.%Y",
)


class TimeParseError(Exception):
    pass


def parse_when(text: str, tz: ZoneInfo, now: datetime | None = None) -> datetime:
    """Parse a time expression into an aware datetime.

    Accepts: now, today, tomorrow, yesterday, +3d / -2h / +90m / +1w,
    ISO dates and datetimes, dd.mm.yyyy, and bare HH:MM (meaning today).
    """
    reference = now or datetime.now(tz)
    token = text.strip().lower()

    keyword = _parse_keyword(token, reference)
    if keyword is not None:
        return keyword

    relative = _parse_relative(token, reference)
    if relative is not None:
        return relative

    clock = _parse_clock(token, reference)
    if clock is not None:
        return clock

    absolute = _parse_absolute(text.strip(), tz)
    if absolute is not None:
        return absolute

    raise TimeParseError(f"Cannot parse time expression: {text!r}")


def parse_duration(text: str) -> timedelta:
    """Parse 90, 90m, 2h, 1h30m into a timedelta."""
    token = text.strip().lower()
    match = DURATION_PATTERN.match(token)
    if not match or not token:
        raise TimeParseError(f"Cannot parse duration: {text!r}")

    hours, minutes, bare = match.groups()
    if bare is not None:
        return timedelta(minutes=int(bare))
    if hours is None and minutes is None:
        raise TimeParseError(f"Cannot parse duration: {text!r}")
    total = timedelta(hours=int(hours or 0), minutes=int(minutes or 0))
    if not total:
        raise TimeParseError(f"Duration must be greater than zero: {text!r}")
    return total


def parse_clock_range(text: str) -> tuple[time, time]:
    """Parse a daily window such as 09:00-17:00."""
    match = CLOCK_RANGE_PATTERN.match(text.strip())
    if not match:
        raise TimeParseError(f"Cannot parse daily window: {text!r} (expected HH:MM-HH:MM)")
    start_hour, start_minute, end_hour, end_minute = (int(part) for part in match.groups())
    start = time(hour=start_hour, minute=start_minute)
    end = time(hour=end_hour, minute=end_minute)
    if start >= end:
        raise TimeParseError(f"Daily window must start before it ends: {text!r}")
    return start, end


def parse_weekdays(text: str) -> set[int]:
    """Parse mon-fri, mon,wed,fri or all into Python weekday indices."""
    token = text.strip().lower()
    if token in ("all", "*"):
        return set(WEEKDAY_INDEX.values())
    if "-" in token:
        return _weekday_span(token)
    days = {_weekday_index(part) for part in token.split(",") if part.strip()}
    if not days:
        raise TimeParseError(f"Cannot parse weekdays: {text!r}")
    return days


def as_datetime(value: date | datetime, tz: ZoneInfo) -> datetime:
    """Normalise a date-or-datetime (all-day events yield dates) to an aware datetime."""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=tz)
        return value
    return datetime.combine(value, time.min, tzinfo=tz)


def merge_intervals(
    intervals: list[tuple[datetime, datetime]],
) -> list[tuple[datetime, datetime]]:
    """Collapse overlapping or touching intervals into a sorted, disjoint list."""
    ordered = sorted(intervals, key=lambda pair: pair[0])
    merged: list[tuple[datetime, datetime]] = []
    for start, end in ordered:
        if end <= start:
            continue
        if merged and start <= merged[-1][1]:
            previous_start, previous_end = merged[-1]
            merged[-1] = (previous_start, max(previous_end, end))
            continue
        merged.append((start, end))
    return merged


def free_slots(
    busy: list[tuple[datetime, datetime]],
    window_start: datetime,
    window_end: datetime,
    duration: timedelta,
    day_start: time,
    day_end: time,
    weekdays: set[int],
) -> list[tuple[datetime, datetime]]:
    """Find gaps of at least `duration` inside the daily windows of the search range."""
    occupied = merge_intervals(busy)
    candidates = _daily_windows(window_start, window_end, day_start, day_end, weekdays)
    slots: list[tuple[datetime, datetime]] = []
    for candidate_start, candidate_end in candidates:
        gaps = _subtract(candidate_start, candidate_end, occupied)
        slots.extend(gap for gap in gaps if gap[1] - gap[0] >= duration)
    return slots


def _weekday_span(token: str) -> set[int]:
    first, _, last = token.partition("-")
    start = _weekday_index(first)
    end = _weekday_index(last)
    if start <= end:
        return set(range(start, end + 1))
    return set(range(start, 7)) | set(range(0, end + 1))


def _weekday_index(name: str) -> int:
    key = name.strip()[:3]
    if key not in WEEKDAY_INDEX:
        raise TimeParseError(f"Unknown weekday: {name!r}")
    return WEEKDAY_INDEX[key]


def _parse_keyword(token: str, reference: datetime) -> datetime | None:
    midnight = reference.replace(hour=0, minute=0, second=0, microsecond=0)
    if token == "now":
        return reference.replace(second=0, microsecond=0)
    if token == "today":
        return midnight
    if token == "tomorrow":
        return midnight + timedelta(days=1)
    if token == "yesterday":
        return midnight - timedelta(days=1)
    return None


def _parse_relative(token: str, reference: datetime) -> datetime | None:
    match = RELATIVE_PATTERN.match(token)
    if not match:
        return None
    sign, amount, unit = match.groups()
    delta = UNIT_TO_DELTA[unit](int(amount))
    if sign == "-":
        return reference - delta
    return reference + delta


def _parse_clock(token: str, reference: datetime) -> datetime | None:
    match = re.match(r"^(\d{1,2}):(\d{2})$", token)
    if not match:
        return None
    hour, minute = int(match.group(1)), int(match.group(2))
    return reference.replace(hour=hour, minute=minute, second=0, microsecond=0)


def _parse_absolute(text: str, tz: ZoneInfo) -> datetime | None:
    for fmt in DATETIME_FORMATS:
        try:
            parsed = datetime.strptime(text, fmt)
        except ValueError:
            continue
        return parsed.replace(tzinfo=tz)
    return None


def _daily_windows(
    window_start: datetime,
    window_end: datetime,
    day_start: time,
    day_end: time,
    weekdays: set[int],
) -> list[tuple[datetime, datetime]]:
    tz = window_start.tzinfo
    windows: list[tuple[datetime, datetime]] = []
    day = window_start.date()
    while day <= window_end.date():
        if day.weekday() not in weekdays:
            day += timedelta(days=1)
            continue
        start = datetime.combine(day, day_start, tzinfo=tz)
        end = datetime.combine(day, day_end, tzinfo=tz)
        clipped_start = max(start, window_start)
        clipped_end = min(end, window_end)
        if clipped_start < clipped_end:
            windows.append((clipped_start, clipped_end))
        day += timedelta(days=1)
    return windows


def _subtract(
    start: datetime,
    end: datetime,
    occupied: list[tuple[datetime, datetime]],
) -> list[tuple[datetime, datetime]]:
    gaps: list[tuple[datetime, datetime]] = []
    cursor = start
    for busy_start, busy_end in occupied:
        if busy_end <= cursor:
            continue
        if busy_start >= end:
            break
        if busy_start > cursor:
            gaps.append((cursor, busy_start))
        cursor = max(cursor, busy_end)
        if cursor >= end:
            return gaps
    if cursor < end:
        gaps.append((cursor, end))
    return gaps
