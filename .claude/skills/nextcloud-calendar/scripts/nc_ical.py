"""Pure iCalendar construction and extraction. No network, no config."""

import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from icalendar import Alarm, Calendar, Event, Todo, vRecur

from nc_time import as_datetime

PRODID = "-//claude-code//nextcloud-calendar skill//EN"
ICAL_VERSION = "2.0"


@dataclass
class EventDraft:
    summary: str
    start: datetime
    end: datetime
    all_day: bool = False
    location: str | None = None
    description: str | None = None
    rrule: str | None = None
    alarm_minutes: int | None = None
    categories: list[str] | None = None


@dataclass
class TodoDraft:
    summary: str
    due: datetime | None = None
    priority: int | None = None
    description: str | None = None
    categories: list[str] | None = None


def build_event(draft: EventDraft, uid: str | None = None) -> str:
    component = Event()
    component.add("uid", uid or new_uid())
    component.add("dtstamp", datetime.now(draft.start.tzinfo))
    _apply_event_fields(component, draft)
    if draft.alarm_minutes is not None:
        alarm = _build_alarm(draft.alarm_minutes, draft.summary)
        component.add_component(alarm)
    return _wrap(component)


def build_todo(draft: TodoDraft, uid: str | None = None) -> str:
    component = Todo()
    component.add("uid", uid or new_uid())
    component.add("dtstamp", datetime.now(tz=(draft.due.tzinfo if draft.due else None)))
    component.add("summary", draft.summary)
    component.add("status", "NEEDS-ACTION")
    if draft.due is not None:
        component.add("due", draft.due)
    if draft.priority is not None:
        component.add("priority", draft.priority)
    if draft.description:
        component.add("description", draft.description)
    if draft.categories:
        component.add("categories", draft.categories)
    return _wrap(component)


def new_uid() -> str:
    return f"{uuid.uuid4()}@claude-code"


def apply_event_changes(component, changes: dict) -> None:
    """Mutate a fetched VEVENT in place. Only keys present in `changes` are touched."""
    setters = {
        "summary": lambda value: _replace(component, "SUMMARY", value),
        "location": lambda value: _replace(component, "LOCATION", value),
        "description": lambda value: _replace(component, "DESCRIPTION", value),
        "start": lambda value: _replace(component, "DTSTART", value),
        "end": lambda value: _replace(component, "DTEND", value),
        "rrule": lambda value: _replace(component, "RRULE", vRecur.from_ical(value)),
        "status": lambda value: _replace(component, "STATUS", value.upper()),
    }
    for key, value in changes.items():
        setter = setters.get(key)
        if setter is None:
            raise KeyError(f"Unsupported event field: {key}")
        setter(value)
    _bump_sequence(component)


def event_record(component, calendar_name: str, tz: ZoneInfo) -> dict:
    """Flatten a VEVENT into a plain dict for rendering and sorting."""
    raw_start = _value_of(component, "DTSTART")
    all_day = isinstance(raw_start, date) and not isinstance(raw_start, datetime)
    start = as_datetime(raw_start, tz) if raw_start is not None else None
    end = _event_end(component, raw_start, tz)
    return {
        "uid": str(component.get("UID", "")),
        "summary": str(component.get("SUMMARY", "(no title)")),
        "calendar": calendar_name,
        "start": start,
        "end": end,
        "all_day": all_day,
        "location": _optional_text(component, "LOCATION"),
        "description": _optional_text(component, "DESCRIPTION"),
        "status": _optional_text(component, "STATUS"),
        "transparent": str(component.get("TRANSP", "")).upper() == "TRANSPARENT",
        "recurring": component.get("RRULE") is not None,
    }


def todo_record(component, calendar_name: str, tz: ZoneInfo) -> dict:
    raw_due = _value_of(component, "DUE")
    priority = component.get("PRIORITY")
    return {
        "uid": str(component.get("UID", "")),
        "summary": str(component.get("SUMMARY", "(no title)")),
        "calendar": calendar_name,
        "due": as_datetime(raw_due, tz) if raw_due is not None else None,
        "status": _optional_text(component, "STATUS") or "NEEDS-ACTION",
        "priority": int(priority) if priority is not None else None,
        "description": _optional_text(component, "DESCRIPTION"),
        "completed": str(component.get("STATUS", "")).upper() == "COMPLETED",
    }


def busy_interval(record: dict) -> tuple[datetime, datetime] | None:
    """Busy time claimed by an event, or None if it does not block the calendar."""
    if record["transparent"]:
        return None
    if (record["status"] or "").upper() == "CANCELLED":
        return None
    if record["start"] is None or record["end"] is None:
        return None
    return record["start"], record["end"]


def _apply_event_fields(component, draft: EventDraft) -> None:
    component.add("summary", draft.summary)
    if draft.all_day:
        component.add("dtstart", draft.start.date())
        component.add("dtend", _exclusive_end_date(draft))
    else:
        component.add("dtstart", draft.start)
        component.add("dtend", draft.end)
    if draft.location:
        component.add("location", draft.location)
    if draft.description:
        component.add("description", draft.description)
    if draft.categories:
        component.add("categories", draft.categories)
    if draft.rrule:
        recurrence = vRecur.from_ical(draft.rrule)
        component.add("rrule", recurrence)


def _exclusive_end_date(draft: EventDraft) -> date:
    """All-day DTEND is exclusive; a single-day event ends the following day."""
    end_date = draft.end.date()
    if end_date <= draft.start.date():
        return draft.start.date() + timedelta(days=1)
    return end_date


def _build_alarm(minutes_before: int, summary: str) -> Alarm:
    alarm = Alarm()
    alarm.add("action", "DISPLAY")
    alarm.add("description", summary)
    alarm.add("trigger", timedelta(minutes=-abs(minutes_before)))
    return alarm


def _wrap(component) -> str:
    calendar = Calendar()
    calendar.add("prodid", PRODID)
    calendar.add("version", ICAL_VERSION)
    calendar.add_component(component)
    return calendar.to_ical().decode("utf-8")


def _replace(component, key: str, value) -> None:
    if key in component:
        del component[key]
    component.add(key, value)


def _bump_sequence(component) -> None:
    current = component.get("SEQUENCE")
    next_value = (int(current) if current is not None else 0) + 1
    _replace(component, "SEQUENCE", next_value)
    _replace(component, "DTSTAMP", datetime.now(tz=None).astimezone())


def _value_of(component, key: str):
    field = component.get(key)
    if field is None:
        return None
    return getattr(field, "dt", field)


def _optional_text(component, key: str) -> str | None:
    value = component.get(key)
    if value is None:
        return None
    return str(value)


def _event_end(component, raw_start, tz: ZoneInfo) -> datetime | None:
    raw_end = _value_of(component, "DTEND")
    if raw_end is not None:
        return as_datetime(raw_end, tz)
    if raw_start is None:
        return None
    duration = _value_of(component, "DURATION")
    start = as_datetime(raw_start, tz)
    if isinstance(duration, timedelta):
        return start + duration
    if isinstance(raw_start, date) and not isinstance(raw_start, datetime):
        return start + timedelta(days=1)
    return start
