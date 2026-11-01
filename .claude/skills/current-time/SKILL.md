---
name: current-time
description: Fetch the current date and time via the command line. Use whenever the current time, date, or timestamp is needed — instead of any Time MCP tool.
---

# Current Time

Fetch the current time with the `date` command via Bash. Do not use MCP time tools.

Local time (with timezone):

```bash
date '+%Y-%m-%d %H:%M:%S %Z (%z)'
```

UTC:

```bash
date -u '+%Y-%m-%d %H:%M:%S UTC'
```

Adjust the format string as needed (e.g. `%s` for a Unix timestamp, `--iso-8601=seconds` for ISO 8601).
