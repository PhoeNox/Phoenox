"""CalDAV I/O against a Nextcloud server."""

from datetime import datetime
from zoneinfo import ZoneInfo

import caldav
from caldav.lib.error import AuthorizationError, DAVError, NotFoundError

from nc_config import Config
from nc_ical import event_record, todo_record

CONNECT_TIMEOUT = 30


class DavError(Exception):
    pass


def connect(config: Config):
    client = caldav.DAVClient(
        url=config.url,
        username=config.username,
        password=config.password,
        timeout=CONNECT_TIMEOUT,
    )
    try:
        return client.principal()
    except AuthorizationError as exc:
        raise DavError(
            "Authentication failed. Check the username and app password "
            "(Nextcloud > Settings > Security > Devices & sessions)."
        ) from exc
    except DAVError as exc:
        raise DavError(f"Cannot reach the CalDAV server at {config.url}: {exc}") from exc


def describe_calendars(principal) -> list[dict]:
    described = []
    for calendar in principal.calendars():
        described.append(
            {
                "name": calendar.name,
                "url": str(calendar.url),
                "components": _supported_components(calendar),
            }
        )
    return described


def select_calendars(principal, names: list[str] | None, fallback: str | None) -> list:
    """Resolve calendar names to Calendar objects; no names means all calendars."""
    available = principal.calendars()
    wanted = names or ([fallback] if fallback else [])
    if not wanted:
        return available

    by_name = {calendar.name: calendar for calendar in available}
    selected = []
    for name in wanted:
        match = by_name.get(name) or _match_loosely(by_name, name)
        if match is None:
            known = ", ".join(sorted(by_name)) or "none"
            raise DavError(f"No calendar named '{name}'. Available: {known}")
        selected.append(match)
    return selected


def fetch_events(
    calendars: list,
    start: datetime,
    end: datetime,
    tz: ZoneInfo,
) -> list[dict]:
    records = []
    for calendar in calendars:
        results = _search(calendar, event=True, start=start, end=end, expand=True)
        for result in results:
            record = event_record(result.icalendar_component, calendar.name, tz)
            records.append(record)
    records.sort(key=lambda record: (record["start"] is None, record["start"]))
    return records


def fetch_todos(calendars: list, include_completed: bool, tz: ZoneInfo) -> list[dict]:
    records = []
    for calendar in calendars:
        results = _search(calendar, todo=True, include_completed=include_completed)
        for result in results:
            record = todo_record(result.icalendar_component, calendar.name, tz)
            records.append(record)
    records.sort(key=lambda record: (record["due"] is None, record["due"]))
    return records


def create_object(calendar, ical: str, is_todo: bool):
    try:
        if is_todo:
            return calendar.save_todo(ical)
        return calendar.save_event(ical)
    except DAVError as exc:
        raise DavError(f"Server rejected the new object: {exc}") from exc


def find_by_uid(calendars: list, uid: str):
    """Locate an event or task by UID across the given calendars."""
    for calendar in calendars:
        try:
            return calendar, calendar.object_by_uid(uid)
        except NotFoundError:
            continue
        except DAVError:
            continue
    raise DavError(f"No event or task with UID {uid} in the searched calendars.")


def delete_object(obj) -> None:
    try:
        obj.delete()
    except DAVError as exc:
        raise DavError(f"Delete failed: {exc}") from exc


def save_object(obj) -> None:
    try:
        obj.save()
    except DAVError as exc:
        raise DavError(f"Save failed: {exc}") from exc


def complete_todo(obj) -> None:
    try:
        obj.complete()
    except DAVError as exc:
        raise DavError(f"Completing the task failed: {exc}") from exc


def _search(calendar, **kwargs) -> list:
    """Search one calendar, tolerating servers that reject a component type."""
    try:
        return calendar.search(**kwargs)
    except (DAVError, ValueError):
        return []


def _supported_components(calendar) -> list[str]:
    try:
        return [str(component) for component in calendar.get_supported_components()]
    except DAVError:
        return []


def _match_loosely(by_name: dict, name: str):
    lowered = name.lower()
    for candidate_name, calendar in by_name.items():
        if candidate_name.lower() == lowered:
            return calendar
    return None
