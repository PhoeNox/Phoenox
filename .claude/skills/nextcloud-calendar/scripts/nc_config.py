"""Configuration and credential loading. Trust boundary: fails fast and loud."""

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

SECRET_SERVICE = "nextcloud-caldav"
ZONEINFO_ROOT = Path("/usr/share/zoneinfo")


def config_path() -> Path:
    override = os.environ.get("NCAL_CONFIG")
    if override:
        return Path(override)
    return Path.home() / ".config" / "nextcloud-caldav" / "config.json"


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Config:
    url: str
    username: str
    password: str
    timezone: ZoneInfo
    default_calendar: str | None


def load_config() -> Config:
    raw = _read_config_file()
    url = _require(raw, "url")
    username = _require(raw, "username")
    password = _read_password(username)
    tz_name = raw.get("timezone") or system_timezone_name()
    tz = _load_timezone(tz_name)
    return Config(
        url=url,
        username=username,
        password=password,
        timezone=tz,
        default_calendar=raw.get("default_calendar"),
    )


def system_timezone_name() -> str:
    """Resolve the system timezone from /etc/localtime, falling back to UTC."""
    localtime = Path("/etc/localtime")
    if not localtime.is_symlink():
        return "UTC"
    target = localtime.resolve()
    try:
        return str(target.relative_to(ZONEINFO_ROOT))
    except ValueError:
        return "UTC"


def _read_config_file() -> dict:
    path = config_path()
    if not path.exists():
        raise ConfigError(
            f"No config at {path}. Run the skill's scripts/setup.sh to create it."
        )
    text = path.read_text(encoding="utf-8")
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"{path} is not valid JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigError(f"{path} must contain a JSON object.")
    return raw


def _require(raw: dict, key: str) -> str:
    value = raw.get(key)
    if not value:
        raise ConfigError(f"Missing '{key}' in {config_path()}.")
    return str(value)


def _read_password(username: str) -> str:
    command = [
        "secret-tool",
        "lookup",
        "service",
        SECRET_SERVICE,
        "username",
        username,
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
    except FileNotFoundError as exc:
        raise ConfigError("secret-tool is not installed (package: libsecret).") from exc
    except subprocess.TimeoutExpired as exc:
        raise ConfigError("secret-tool timed out; is the keyring unlocked?") from exc

    password = result.stdout.strip()
    if result.returncode != 0 or not password:
        raise ConfigError(
            f"No app password in the keyring for service '{SECRET_SERVICE}', "
            f"username '{username}'. Run the skill's scripts/setup.sh."
        )
    return password


def _load_timezone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except Exception as exc:
        raise ConfigError(f"Unknown timezone '{name}'.") from exc
