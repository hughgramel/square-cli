"""Square API client wrapper."""

from __future__ import annotations

from typing import Any

from square.client import Square
from square.environment import SquareEnvironment

from . import config as cfg
from .errors import AuthError


def get_client(
    access_token: str | None = None,
    profile: str = "default",
    sandbox: bool = False,
    config_overrides: dict[str, Any] | None = None,
) -> Square:
    """Create an authenticated Square client.

    Token resolution order:
    1. Explicit access_token parameter
    2. SQUARE_ACCESS_TOKEN environment variable
    3. OS keychain (via keyring)
    """
    effective_profile = cfg.resolve_profile(profile, sandbox)
    token = access_token or cfg.get_access_token(effective_profile)
    if not token:
        hint = 'Run "square login" to authenticate, or set SQUARE_ACCESS_TOKEN.'
        if sandbox:
            hint = 'Run "square login --token --sandbox" to authenticate for sandbox.'
        raise AuthError("Not authenticated.", hint=hint)

    profile_cfg = cfg.load_config(profile=effective_profile)
    if config_overrides:
        profile_cfg.update(config_overrides)

    env_str = "sandbox" if sandbox else cfg.get_environment(profile_cfg)
    environment = (
        SquareEnvironment.SANDBOX if env_str == "sandbox" else SquareEnvironment.PRODUCTION
    )

    return Square(
        token=token,
        environment=environment,
    )


def get_location_id(
    client: Square,
    location_id: str | None = None,
    profile: str = "default",
    sandbox: bool = False,
) -> str:
    """Resolve the location ID from arg, config, or API.

    Resolution order:
    1. Explicit location_id argument
    2. Config file (location_id setting)
    3. First location from the API (if merchant has exactly one)
    """
    if location_id:
        return location_id

    effective_profile = cfg.resolve_profile(profile, sandbox=sandbox)
    profile_cfg = cfg.load_config(profile=effective_profile)
    configured = profile_cfg.get("location_id")
    if configured:
        return configured

    # Try to auto-detect if there's only one location
    locations_page = client.locations.list()
    locations = locations_page.locations or []

    if len(locations) == 1:
        return locations[0].id

    if len(locations) == 0:
        raise AuthError(
            "No locations found for this account.",
            hint="Check your Square account has at least one active location.",
        )

    location_names = [
        f"  {loc.id}: {loc.name or 'Unnamed'}"
        for loc in locations[:10]
    ]
    raise AuthError(
        "Multiple locations found. Please specify one.",
        hint=(
            'Run "square locations list" to see your locations, then\n'
            '  "square locations set-default <id>" to set a default.\n\n'
            "Available locations:\n" + "\n".join(location_names)
        ),
    )
