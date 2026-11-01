#!/usr/bin/env python3
"""CLI for managing Nextcloud calendars and tasks over CalDAV."""

import argparse
import sys
from datetime import datetime

import nc_dav
import nc_view
from nc_config import ConfigError, load_config
from nc_dav import DavError
from nc_ical import (
    EventDraft,
    TodoDraft,
    apply_event_changes,
    build_event,
    build_todo,
    busy_interval,
    event_record,
)
from nc_time import (
    TimeParseError,
    free_slots,
    merge_intervals,
    parse_clock_range,
    parse_duration,
    parse_weekdays,
    parse_when,
)

DEFAULT_RANGE_START = "today"
DEFAULT_RANGE_END = "+30d"
DEFAULT_WORKDAY = "09:00-17:00"
DEFAULT_DAYS = "mon-fri"


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        output = dispatch(args)
    except (ConfigError, DavError, TimeParseError, KeyError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(output)
    return 0


def dispatch(args) -> str:
    handlers = {
        "calendars": cmd_calendars,
        "events": cmd_events,
        "event-show": cmd_event_show,
        "event-create": cmd_event_create,
        "event-update": cmd_event_update,
        "event-delete": cmd_event_delete,
        "tasks": cmd_tasks,
        "task-create": cmd_task_create,
        "task-complete": cmd_task_complete,
        "task-delete": cmd_task_delete,
        "busy": cmd_busy,
        "slots": cmd_slots,
    }
    return handlers[args.command](args)


# --- commands ---------------------------------------------------------------


def cmd_calendars(args) -> str:
    config = load_config()
    principal = nc_dav.connect(config)
    calendars = nc_dav.describe_calendars(principal)
    return nc_view.render(calendars, args.json, nc_view.render_calendars)


def cmd_events(args) -> str:
    config = load_config()
    principal = nc_dav.connect(config)
    calendars = nc_dav.select_calendars(principal, args.calendar, config.default_calendar)
    start, end = resolve_range(args, config)
    events = nc_dav.fetch_events(calendars, start, end, config.timezone)
    matching = filter_events(events, args.search)
    return nc_view.render(matching, args.json, nc_view.render_events)


def cmd_event_show(args) -> str:
    config = load_config()
    principal = nc_dav.connect(config)
    calendars = nc_dav.select_calendars(principal, args.calendar, None)
    calendar, obj = nc_dav.find_by_uid(calendars, args.uid)
    record = event_record(obj.icalendar_component, calendar.name, config.timezone)
    return nc_view.render(record, args.json, nc_view.render_event_detail)


def cmd_event_create(args) -> str:
    config = load_config()
    principal = nc_dav.connect(config)
    calendars = nc_dav.select_calendars(principal, args.calendar, config.default_calendar)
    target = single_calendar(calendars, "event-create")
    draft = build_event_draft(args, config)
    ical = build_event(draft)
    created = nc_dav.create_object(target, ical, is_todo=False)
    uid = str(created.icalendar_component.get("UID", ""))
    return f"Created '{draft.summary}' in [{target.name}]\nUID {uid}"


def cmd_event_update(args) -> str:
    config = load_config()
    principal = nc_dav.connect(config)
    calendars = nc_dav.select_calendars(principal, args.calendar, None)
    calendar, obj = nc_dav.find_by_uid(calendars, args.uid)
    changes = collect_event_changes(args, config)
    if not changes:
        return "Nothing to update; pass at least one field flag."
    with obj.edit_icalendar_component() as component:
        apply_event_changes(component, changes)
    nc_dav.save_object(obj)
    fields = ", ".join(sorted(changes))
    return f"Updated {fields} on {args.uid} in [{calendar.name}]"


def cmd_event_delete(args) -> str:
    return delete_by_uid(args, "event")


def cmd_tasks(args) -> str:
    config = load_config()
    principal = nc_dav.connect(config)
    calendars = nc_dav.select_calendars(principal, args.calendar, config.default_calendar)
    todos = nc_dav.fetch_todos(calendars, args.all, config.timezone)
    return nc_view.render(todos, args.json, nc_view.render_todos)


def cmd_task_create(args) -> str:
    config = load_config()
    principal = nc_dav.connect(config)
    calendars = nc_dav.select_calendars(principal, args.calendar, config.default_calendar)
    target = single_calendar(calendars, "task-create")
    draft = build_todo_draft(args, config)
    ical = build_todo(draft)
    nc_dav.create_object(target, ical, is_todo=True)
    return f"Created task '{draft.summary}' in [{target.name}]"


def cmd_task_complete(args) -> str:
    config = load_config()
    principal = nc_dav.connect(config)
    calendars = nc_dav.select_calendars(principal, args.calendar, None)
    calendar, obj = nc_dav.find_by_uid(calendars, args.uid)
    nc_dav.complete_todo(obj)
    return f"Completed task {args.uid} in [{calendar.name}]"


def cmd_task_delete(args) -> str:
    return delete_by_uid(args, "task")


def cmd_busy(args) -> str:
    config = load_config()
    principal = nc_dav.connect(config)
    calendars = nc_dav.select_calendars(principal, args.calendar, config.default_calendar)
    start, end = resolve_range(args, config)
    events = nc_dav.fetch_events(calendars, start, end, config.timezone)
    blocks = busy_blocks(events)
    return nc_view.render(blocks, args.json, nc_view.render_busy)


def cmd_slots(args) -> str:
    config = load_config()
    principal = nc_dav.connect(config)
    calendars = nc_dav.select_calendars(principal, args.calendar, config.default_calendar)
    start, end = resolve_range(args, config)
    events = nc_dav.fetch_events(calendars, start, end, config.timezone)
    intervals = [interval for interval in map(busy_interval, events) if interval]
    duration = parse_duration(args.duration)
    day_start, day_end = parse_clock_range(args.workday)
    weekdays = parse_weekdays(args.days)
    found = free_slots(intervals, start, end, duration, day_start, day_end, weekdays)
    slots = [as_slot(slot) for slot in found]
    return nc_view.render(slots, args.json, nc_view.render_slots)


# --- shared composition helpers --------------------------------------------


def delete_by_uid(args, label: str) -> str:
    if not args.yes:
        return f"Refusing to delete {args.uid}: pass --yes to confirm."
    config = load_config()
    principal = nc_dav.connect(config)
    calendars = nc_dav.select_calendars(principal, args.calendar, None)
    calendar, obj = nc_dav.find_by_uid(calendars, args.uid)
    summary = str(obj.icalendar_component.get("SUMMARY", ""))
    nc_dav.delete_object(obj)
    return f"Deleted {label} '{summary}' ({args.uid}) from [{calendar.name}]"


def resolve_range(args, config) -> tuple[datetime, datetime]:
    start = parse_when(args.start or DEFAULT_RANGE_START, config.timezone)
    end = parse_when(args.end or DEFAULT_RANGE_END, config.timezone)
    if end <= start:
        raise ValueError("--to must be after --from")
    return start, end


def single_calendar(calendars: list, command: str):
    if len(calendars) != 1:
        raise ValueError(
            f"{command} needs exactly one calendar; pass --calendar NAME "
            "or set default_calendar in the config."
        )
    return calendars[0]


def build_event_draft(args, config) -> EventDraft:
    start = parse_when(args.start, config.timezone)
    end = resolve_event_end(args, start, config)
    return EventDraft(
        summary=args.summary,
        start=start,
        end=end,
        all_day=args.all_day,
        location=args.location,
        description=args.description,
        rrule=args.rrule,
        alarm_minutes=args.alarm,
        categories=split_categories(args.categories),
    )


def resolve_event_end(args, start: datetime, config) -> datetime:
    if args.end:
        return parse_when(args.end, config.timezone)
    if args.duration:
        return start + parse_duration(args.duration)
    return start + parse_duration("60m")


def build_todo_draft(args, config) -> TodoDraft:
    due = parse_when(args.due, config.timezone) if args.due else None
    return TodoDraft(
        summary=args.summary,
        due=due,
        priority=args.priority,
        description=args.description,
        categories=split_categories(args.categories),
    )


def collect_event_changes(args, config) -> dict:
    changes = {}
    text_fields = {
        "summary": args.summary,
        "location": args.location,
        "description": args.description,
        "rrule": args.rrule,
        "status": args.status,
    }
    for key, value in text_fields.items():
        if value is not None:
            changes[key] = value
    if args.start:
        changes["start"] = parse_when(args.start, config.timezone)
    if args.end:
        changes["end"] = parse_when(args.end, config.timezone)
    return changes


def filter_events(events: list[dict], needle: str | None) -> list[dict]:
    if not needle:
        return events
    lowered = needle.lower()
    fields = ("summary", "location", "description")
    matches = []
    for event in events:
        haystack = " ".join(str(event.get(field) or "") for field in fields).lower()
        if lowered in haystack:
            matches.append(event)
    return matches


def busy_blocks(events: list[dict]) -> list[dict]:
    blocks = []
    for event in events:
        interval = busy_interval(event)
        if interval is None:
            continue
        blocks.append({"start": interval[0], "end": interval[1], "summary": event["summary"]})
    return blocks


def as_slot(slot: tuple[datetime, datetime]) -> dict:
    start, end = slot
    minutes = int((end - start).total_seconds() // 60)
    return {"start": start, "end": end, "minutes": minutes}


# --- argument parsing -------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ncal", description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_calendars_parser(subparsers)
    add_events_parser(subparsers)
    add_event_show_parser(subparsers)
    add_event_create_parser(subparsers)
    add_event_update_parser(subparsers)
    add_uid_parser(subparsers, "event-delete", "Delete an event (needs --yes)")
    add_tasks_parser(subparsers)
    add_task_create_parser(subparsers)
    add_uid_parser(subparsers, "task-complete", "Mark a task completed", confirm=False)
    add_uid_parser(subparsers, "task-delete", "Delete a task (needs --yes)")
    add_busy_parser(subparsers)
    add_slots_parser(subparsers)
    return parser


def add_common_flags(parser) -> None:
    parser.add_argument("--calendar", action="append", help="Calendar name; repeatable")
    parser.add_argument("--json", action="store_true", help="Emit JSON")


def add_range_flags(parser) -> None:
    parser.add_argument("--from", dest="start", help=f"Range start (default {DEFAULT_RANGE_START})")
    parser.add_argument("--to", dest="end", help=f"Range end (default {DEFAULT_RANGE_END})")


def add_calendars_parser(subparsers) -> None:
    parser = subparsers.add_parser("calendars", help="List available calendars")
    parser.add_argument("--json", action="store_true", help="Emit JSON")


def add_events_parser(subparsers) -> None:
    parser = subparsers.add_parser("events", help="List events in a time range")
    add_common_flags(parser)
    add_range_flags(parser)
    parser.add_argument("--search", help="Case-insensitive substring filter")


def add_event_show_parser(subparsers) -> None:
    parser = subparsers.add_parser("event-show", help="Show one event by UID")
    add_common_flags(parser)
    parser.add_argument("uid")


def add_event_create_parser(subparsers) -> None:
    parser = subparsers.add_parser("event-create", help="Create an event")
    add_common_flags(parser)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--from", dest="start", required=True)
    parser.add_argument("--to", dest="end")
    parser.add_argument("--duration", help="e.g. 90m, 1h30m (default 60m)")
    parser.add_argument("--all-day", action="store_true")
    parser.add_argument("--location")
    parser.add_argument("--description")
    parser.add_argument("--rrule", help="e.g. FREQ=WEEKLY;BYDAY=MO;COUNT=8")
    parser.add_argument("--alarm", type=int, help="Reminder minutes before start")
    parser.add_argument("--categories", help="Comma-separated")


def add_event_update_parser(subparsers) -> None:
    parser = subparsers.add_parser("event-update", help="Update fields of an event")
    add_common_flags(parser)
    parser.add_argument("uid")
    parser.add_argument("--summary")
    parser.add_argument("--from", dest="start")
    parser.add_argument("--to", dest="end")
    parser.add_argument("--location")
    parser.add_argument("--description")
    parser.add_argument("--rrule")
    parser.add_argument("--status", help="CONFIRMED, TENTATIVE or CANCELLED")


def add_uid_parser(subparsers, name: str, help_text: str, confirm: bool = True) -> None:
    parser = subparsers.add_parser(name, help=help_text)
    add_common_flags(parser)
    parser.add_argument("uid")
    if confirm:
        parser.add_argument("--yes", action="store_true", help="Confirm the deletion")


def add_tasks_parser(subparsers) -> None:
    parser = subparsers.add_parser("tasks", help="List tasks (VTODO)")
    add_common_flags(parser)
    parser.add_argument("--all", action="store_true", help="Include completed tasks")


def add_task_create_parser(subparsers) -> None:
    parser = subparsers.add_parser("task-create", help="Create a task")
    add_common_flags(parser)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--due")
    parser.add_argument("--priority", type=int, help="1 (high) to 9 (low)")
    parser.add_argument("--description")
    parser.add_argument("--categories", help="Comma-separated")


def add_busy_parser(subparsers) -> None:
    parser = subparsers.add_parser("busy", help="Show busy blocks in a range")
    add_common_flags(parser)
    add_range_flags(parser)


def add_slots_parser(subparsers) -> None:
    parser = subparsers.add_parser("slots", help="Find free slots in a range")
    add_common_flags(parser)
    add_range_flags(parser)
    parser.add_argument("--duration", default="60m", help="Minimum slot length (default 60m)")
    parser.add_argument("--workday", default=DEFAULT_WORKDAY, help="Daily window HH:MM-HH:MM")
    parser.add_argument("--days", default=DEFAULT_DAYS, help="e.g. mon-fri or mon,wed,fri")


def split_categories(value: str | None) -> list[str] | None:
    if not value:
        return None
    return [item.strip() for item in value.split(",") if item.strip()]


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
