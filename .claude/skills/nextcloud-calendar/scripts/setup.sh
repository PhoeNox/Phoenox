#!/usr/bin/env bash
# One-time setup: Python venv, keyring entry and config file for the
# nextcloud-calendar skill. Safe to re-run; it overwrites the stored values.
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$SKILL_DIR/.venv"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/nextcloud-caldav"
CONFIG_FILE="$CONFIG_DIR/config.json"
SECRET_SERVICE="nextcloud-caldav"

command -v secret-tool >/dev/null || { echo "secret-tool missing (package: libsecret)" >&2; exit 1; }
command -v python3 >/dev/null || { echo "python3 missing" >&2; exit 1; }

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  echo "Creating venv at $VENV_DIR"
  python3 -m venv "$VENV_DIR"
fi
"$VENV_DIR/bin/pip" -q install --upgrade caldav icalendar

read -r -p "Nextcloud CalDAV URL (e.g. https://cloud.example.com/remote.php/dav): " NC_URL
read -r -p "Nextcloud username: " NC_USER
read -r -p "Default calendar name (optional, Enter to skip): " NC_CALENDAR
DEFAULT_TZ="$(python3 -c 'import sys; sys.path.insert(0, "'"$SKILL_DIR/scripts"'"); from nc_config import system_timezone_name; print(system_timezone_name())')"
read -r -p "Timezone [$DEFAULT_TZ]: " NC_TZ
NC_TZ="${NC_TZ:-$DEFAULT_TZ}"

echo
echo "App password: create one at Nextcloud > Settings > Security > 'Create new app password'."
echo "It is stored in the login keyring, not on disk."
secret-tool store --label="Nextcloud CalDAV ($NC_USER)" service "$SECRET_SERVICE" username "$NC_USER"

if [[ -n "$NC_CALENDAR" ]]; then
  DEFAULT_CAL_JSON="\"$NC_CALENDAR\""
else
  DEFAULT_CAL_JSON="null"
fi

mkdir -p "$CONFIG_DIR"
umask 077
cat >"$CONFIG_FILE" <<EOF
{
  "url": "$NC_URL",
  "username": "$NC_USER",
  "timezone": "$NC_TZ",
  "default_calendar": $DEFAULT_CAL_JSON
}
EOF
chmod 600 "$CONFIG_FILE"

echo
echo "Wrote $CONFIG_FILE"
echo "Verify with: $VENV_DIR/bin/python $SKILL_DIR/scripts/ncal.py calendars"
