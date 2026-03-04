"""Configuration management for Square CLI."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib  # type: ignore[no-redef]


DEFAULT_CONFIG_DIR = Path.home() / ".config" / "square"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.toml"

DEFAULTS: dict[str, Any] = {
    "environment": "production",
    "location_id": "",
    "color": "auto",
    "format": "table",
    "log_level": "info",
}

KEYRING_SERVICE = "square-cli"


def resolve_profile(profile: str, sandbox: bool = False) -> str:
    """Return the effective profile name, appending '-sandbox' for sandbox mode."""
    if sandbox and not profile.endswith("-sandbox"):
        return f"{profile}-sandbox"
    return profile


def config_dir() -> Path:
    """Return the config directory, creating it if needed."""
    d = Path(os.environ.get("SQUARE_CONFIG_DIR", str(DEFAULT_CONFIG_DIR)))
    d.mkdir(parents=True, exist_ok=True)
    return d


def config_path(override: str | None = None) -> Path:
    """Return the config file path."""
    if override:
        return Path(override)
    return config_dir() / "config.toml"


def load_config(path: Path | None = None, profile: str = "default") -> dict[str, Any]:
    """Load configuration for a given profile."""
    p = path or config_path()
    cfg: dict[str, Any] = dict(DEFAULTS)

    if p.exists():
        with open(p, "rb") as f:
            data = tomllib.load(f)
        profile_data = data.get(profile, {})
        cfg.update(profile_data)

    return cfg


def save_config(values: dict[str, Any], path: Path | None = None, profile: str = "default") -> None:
    """Save configuration values for a profile.

    Reads the existing file, updates the profile section, and writes back.
    """
    p = path or config_path()
    existing: dict[str, dict[str, Any]] = {}

    if p.exists():
        with open(p, "rb") as f:
            existing = tomllib.load(f)

    if profile not in existing:
        existing[profile] = {}
    existing[profile].update(values)

    _write_toml(existing, p)


def unset_config(key: str, path: Path | None = None, profile: str = "default") -> bool:
    """Remove a key from a profile. Returns True if key existed."""
    p = path or config_path()
    if not p.exists():
        return False

    with open(p, "rb") as f:
        data = tomllib.load(f)

    if profile in data and key in data[profile]:
        del data[profile][key]
        _write_toml(data, p)
        return True
    return False


def get_access_token(profile: str = "default") -> str | None:
    """Get the access token, checking env var first, then keychain."""
    env_token = os.environ.get("SQUARE_ACCESS_TOKEN")
    if env_token:
        return env_token

    try:
        import keyring

        return keyring.get_password(KEYRING_SERVICE, f"{profile}:access_token")
    except Exception:
        return None


def save_access_token(token: str, profile: str = "default") -> None:
    """Store access token in the OS keychain."""
    import keyring

    keyring.set_password(KEYRING_SERVICE, f"{profile}:access_token", token)


def save_refresh_token(token: str, profile: str = "default") -> None:
    """Store refresh token in the OS keychain."""
    import keyring

    keyring.set_password(KEYRING_SERVICE, f"{profile}:refresh_token", token)


def get_refresh_token(profile: str = "default") -> str | None:
    """Get the refresh token from the OS keychain."""
    try:
        import keyring

        return keyring.get_password(KEYRING_SERVICE, f"{profile}:refresh_token")
    except Exception:
        return None


def delete_tokens(profile: str = "default") -> None:
    """Remove all stored tokens for a profile."""
    try:
        import keyring

        for key in ("access_token", "refresh_token"):
            try:
                keyring.delete_password(KEYRING_SERVICE, f"{profile}:{key}")
            except keyring.errors.PasswordDeleteError:
                pass
    except Exception:
        pass


def get_environment(cfg: dict[str, Any]) -> str:
    """Determine the Square environment (production or sandbox)."""
    env = os.environ.get("SQUARE_ENVIRONMENT")
    if env:
        return env
    return cfg.get("environment", "production")


def _write_toml(data: dict[str, Any], path: Path) -> None:
    """Write a dict as TOML. Simple writer for flat profile sections."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for section, values in data.items():
        lines.append(f"[{section}]")
        if isinstance(values, dict):
            for k, v in values.items():
                if isinstance(v, str):
                    lines.append(f'{k} = "{v}"')
                elif isinstance(v, bool):
                    lines.append(f"{k} = {'true' if v else 'false'}")
                else:
                    lines.append(f"{k} = {v}")
        lines.append("")
    path.write_text("\n".join(lines))
