---
name: nextcloud-calendar
description: Read and manage Nextcloud calendars and tasks over CalDAV — list calendars, list/search events, create/update/delete events, manage VTODO tasks, and find busy blocks or free slots. Use whenever the user asks about their calendar, appointments, schedule, availability, or Nextcloud tasks.
---

# Nextcloud Calendar (CalDAV)

CLI wrapper around the `caldav` library. All commands go through one entry point:

```bash
~/.claude/skills/nextcloud-calendar/.venv/bin/python \
  ~/.claude/skills/nextcloud-calendar/scripts/ncal.py <command> [flags]
```

Add `--json` to any read command for machine-parsable output.

## Setup

If a command reports a missing config or keyring entry, the user must run setup themselves (it prompts for a password):

    ! ~/.claude/skills/nextcloud-calendar/scripts/setup.sh

It stores the app password in the login keyring (`secret-tool`, service `nextcloud-caldav`) and writes `~/.config/nextcloud-caldav/config.json` with `url`, `username`, `timezone`, `default_calendar`. Never ask for, print, or write the password.

## Commands

| Command | Purpose |
| --- | --- |
| `calendars` | List calendars and their supported components |
| `events` | List events in a range (`--from`, `--to`, `--search`) |
| `event-show UID` | Full detail of one event |
| `event-create` | Create an event |
| `event-update UID` | Change fields of an existing event |
| `event-delete UID --yes` | Delete an event |
| `tasks` | List open tasks (`--all` includes completed) |
| `task-create` | Create a task |
| `task-complete UID` | Mark a task done |
| `task-delete UID --yes` | Delete a task |
| `busy` | Busy blocks in a range |
| `slots` | Free slots matching a duration and daily window |

`--calendar NAME` is repeatable and restricts the operation; omitted, reads span all calendars and writes fall back to `default_calendar`. Create commands need exactly one calendar.

## Time expressions

`--from` / `--to` / `--due` accept: `now`, `today`, `tomorrow`, `yesterday`, `+3d` `-2h` `+90m` `+1w`, `2026-07-30`, `2026-07-30T14:00`, `30.07.2026 14:00`, `14:00` (today).

Durations: `90m`, `2h`, `1h30m`, or a bare number of minutes.

## Examples

```bash
# What's on this week
ncal.py events --from today --to +7d

# Search one calendar
ncal.py events --calendar Arbeit --from -30d --to +30d --search dentist --json

# Timed event with a reminder
ncal.py event-create --calendar Privat --summary "Zahnarzt" \
  --from "2026-08-04 09:30" --duration 45m --location "Praxis Dr. Meyer" --alarm 30

# All-day, recurring
ncal.py event-create --calendar Privat --summary "Urlaub" \
  --from 2026-08-10 --to 2026-08-21 --all-day
ncal.py event-create --calendar Arbeit --summary "Standup" \
  --from "2026-08-03 09:00" --duration 15m --rrule "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR;COUNT=40"

# Move an event
ncal.py event-update <uid> --from "2026-08-04 11:00" --to "2026-08-04 12:00"

# Tasks
ncal.py tasks
ncal.py task-create --summary "Steuer abgeben" --due +14d --priority 1

# Availability
ncal.py busy --from today --to +5d
ncal.py slots --from tomorrow --to +14d --duration 90m --workday 09:00-17:00 --days mon-fri
```

## Working rules

- Resolve "next Tuesday", "in two weeks" against the real current date first — use the `current-time` skill, do not assume.
- Before any create, update or delete: state calendar, title, and exact start/end, and get explicit confirmation. `--yes` is required for deletes; never add it pre-emptively.
- Find UIDs with `events --json` or `tasks --json`; never invent one.
- Recurring events: `event-update` and `event-delete` act on the whole series, not one occurrence. Say so before touching a recurring item.
- `slots` treats `TRANSPARENT` and `CANCELLED` events as free; everything else, including all-day events, blocks time.
- On `error: ...` output, report the message as-is rather than retrying blindly — auth and keyring failures need the user.
