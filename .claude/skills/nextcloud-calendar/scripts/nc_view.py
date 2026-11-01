"""Pure rendering of records to text or JSON."""

import json
from datetime import datetime

DATE_FORMAT = "%a %Y-%m-%d"
TIME_FORMAT = "%H:%M"


def render(payload, as_json: bool, renderer) -> str:
    if as_json:
        return json.dumps(payload, indent=2, default=_json_default, ensure_ascii=False)
    return renderer(payload)


def render_calendars(calendars: list[dict]) -> str:
    if not calendars:
        return "No calendars found."
    lines = []
    for calendar in calendars:
        components = ", ".join(calendar["components"]) or "-"
        lines.append(f"{calendar['name']}  [{components}]")
        lines.append(f"    {calendar['url']}")
    return "\n".join(lines)


def render_events(events: list[dict]) -> str:
    if not events:
        return "No events in range."
    lines = []
    for day, group in _group_by_day(events):
        lines.append(day)
        lines.extend(f"  {_event_line(event)}" for event in group)
    return "\n".join(lines)


def render_event_detail(event: dict) -> str:
    rows = [
        ("Summary", event["summary"]),
        ("Calendar", event["calendar"]),
        ("Start", _stamp(event["start"], event["all_day"])),
        ("End", _stamp(event["end"], event["all_day"])),
        ("Location", event["location"]),
        ("Status", event["status"]),
        ("Recurring", "yes" if event["recurring"] else "no"),
        ("UID", event["uid"]),
        ("Description", event["description"]),
    ]
    return "\n".join(f"{label:<12}{value}" for label, value in rows if value not in (None, ""))


def render_todos(todos: list[dict]) -> str:
    if not todos:
        return "No tasks."
    lines = []
    for todo in todos:
        mark = "x" if todo["completed"] else " "
        due = _stamp(todo["due"], False) if todo["due"] else "no due date"
        priority = f" !{todo['priority']}" if todo["priority"] else ""
        lines.append(f"[{mark}] {todo['summary']}{priority}  ({due})  [{todo['calendar']}]")
        lines.append(f"      {todo['uid']}")
    return "\n".join(lines)


def render_busy(intervals: list[dict]) -> str:
    if not intervals:
        return "No busy time in range."
    lines = []
    for day, group in _group_by_day(intervals):
        lines.append(day)
        for interval in group:
            span = f"{interval['start'].strftime(TIME_FORMAT)}-{interval['end'].strftime(TIME_FORMAT)}"
            lines.append(f"  {span}  {interval['summary']}")
    return "\n".join(lines)


def render_slots(slots: list[dict]) -> str:
    if not slots:
        return "No free slots matching the constraints."
    lines = []
    for day, group in _group_by_day(slots):
        lines.append(day)
        for slot in group:
            span = f"{slot['start'].strftime(TIME_FORMAT)}-{slot['end'].strftime(TIME_FORMAT)}"
            lines.append(f"  {span}  ({slot['minutes']} min)")
    return "\n".join(lines)


def _group_by_day(items: list[dict]) -> list[tuple[str, list[dict]]]:
    groups: dict[str, list[dict]] = {}
    for item in items:
        key = item["start"].strftime(DATE_FORMAT)
        groups.setdefault(key, []).append(item)
    return list(groups.items())


def _event_line(event: dict) -> str:
    when = "all day" if event["all_day"] else _span(event)
    parts = [f"{when:<13}", event["summary"]]
    if event["location"]:
        parts.append(f"@ {event['location']}")
    parts.append(f"[{event['calendar']}]")
    return "  ".join(parts)


def _span(event: dict) -> str:
    start = event["start"].strftime(TIME_FORMAT)
    end = event["end"].strftime(TIME_FORMAT) if event["end"] else "?"
    return f"{start}-{end}"


def _stamp(value: datetime | None, all_day: bool) -> str | None:
    if value is None:
        return None
    if all_day:
        return value.strftime(DATE_FORMAT)
    return value.strftime(f"{DATE_FORMAT} {TIME_FORMAT}")


def _json_default(value):
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)
