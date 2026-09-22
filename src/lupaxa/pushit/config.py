"""Load Pushit profiles from a YAML config file."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn

import yaml

from .client import (
    DEFAULT_TIMEOUT,
    MAX_TITLE,
    MAX_URL,
    MAX_URL_TITLE,
    require_text,
    require_timeout,
)

_PROFILE_FIELDS = (
    "user_key",
    "api_token",
    "title",
    "url",
    "url_title",
    "sound",
    "device",
    "priority",
    "timeout",
    "retry",
    "expire",
)
_PRIORITIES = frozenset({-2, -1, 0, 1})
_OPEN_LIMIT = 10**6


class ConfigError(ValueError):
    """The config file or selected profile cannot be used."""


@dataclass(frozen=True)
class Profile:
    """One named block of Pushover settings from the config file."""

    user_key: str | None = None
    api_token: str | None = None
    title: str | None = None
    url: str | None = None
    url_title: str | None = None
    sound: str | None = None
    device: str | None = None
    priority: int | None = None
    timeout: float | None = None
    retry: int | None = None
    expire: int | None = None


@dataclass(frozen=True)
class ResolvedSettings:
    """Settings after CLI flags override a profile."""

    user_key: str | None
    api_token: str
    title: str | None
    url: str | None
    url_title: str | None
    sound: str | None
    device: str | None
    priority: int
    timeout: float
    retry: int
    expire: int


def default_config_path() -> Path:
    """Return the default config path, ``$HOME/.pushit.yml``."""
    return Path.home() / ".pushit.yml"


def load_profile(name: str, path: Path | None = None) -> Profile:
    """Load ``name`` from ``path`` or from ``$HOME/.pushit.yml``."""
    config_path = default_config_path() if path is None else path
    yaml_secrets: tuple[str, ...] = ()
    try:
        if not config_path.is_file():
            raise ConfigError(f"config file not found: {config_path}")
        loaded, yaml_secrets = _read_config(config_path)
        return _load_named_profile(name, loaded, config_path)
    except ConfigError as exc:
        _reraise_config_error(exc, *yaml_secrets)


def _load_named_profile(name: str, loaded: object, config_path: Path) -> Profile:
    profiles = _profiles(loaded, config_path)
    if name not in profiles:
        raise ConfigError(f"profile not found: {name}")
    raw = profiles[name]
    if not isinstance(raw, dict):
        raise ConfigError(f"profile {name} must be a mapping")
    secrets = _profile_secrets(raw)
    unknown = sorted(str(key) for key in raw if key not in _PROFILE_FIELDS)
    if unknown:
        _raise_config_error(f"unknown profile setting: {', '.join(unknown)}", *secrets)
    return Profile(
        user_key=_optional_text(raw.get("user_key"), "user_key", _OPEN_LIMIT, *secrets),
        api_token=_optional_text(raw.get("api_token"), "api_token", _OPEN_LIMIT, *secrets),
        title=_optional_text(raw.get("title"), "title", MAX_TITLE, *secrets),
        url=_optional_text(raw.get("url"), "url", MAX_URL, *secrets),
        url_title=_optional_text(raw.get("url_title"), "url_title", MAX_URL_TITLE, *secrets),
        sound=_optional_text(raw.get("sound"), "sound", _OPEN_LIMIT, *secrets),
        device=_optional_text(raw.get("device"), "device", _OPEN_LIMIT, *secrets),
        priority=_optional_priority(raw.get("priority"), *secrets),
        timeout=_optional_timeout(raw.get("timeout"), *secrets),
        retry=_optional_retry(raw.get("retry"), *secrets),
        expire=_optional_expire(raw.get("expire"), *secrets),
    )


def resolve_settings(
    *,
    profile_name: str | None,
    config_path: Path | None,
    user_key: str | None,
    api_token: str | None,
    title: str | None,
    url: str | None,
    url_title: str | None,
    sound: str | None,
    device: str | None,
    priority: int | None,
    timeout: float | None,
    retry: int | None,
    expire: int | None,
) -> ResolvedSettings:
    """Merge CLI values over an optional profile.

    A passed CLI value wins. ``priority`` falls back to 0, ``timeout`` to
    ``DEFAULT_TIMEOUT``, ``retry`` to 30, and ``expire`` to 3600.
    """
    cli_secrets = _cli_secrets(user_key=user_key, api_token=api_token)
    yaml_secrets: tuple[str, ...] = ()
    profile: Profile | None = None
    try:
        if profile_name is None and config_path is not None:
            _raise_config_error(
                "--profile is required when --config is set",
                *cli_secrets,
            )
        if profile_name:
            config_file = default_config_path() if config_path is None else config_path
            if config_file.is_file():
                _, yaml_secrets = _read_config(config_file)
            profile = load_profile(profile_name, config_path)
        secrets = _settings_secrets(profile, user_key=user_key, api_token=api_token)
        resolved_url = _pick_text(
            url,
            None if profile is None else profile.url,
            "url",
            MAX_URL,
            *secrets,
        )
        resolved_url_title = _pick_text(
            url_title,
            None if profile is None else profile.url_title,
            "url_title",
            MAX_URL_TITLE,
            *secrets,
        )
        if resolved_url_title is not None and resolved_url is None:
            _raise_config_error("url_title requires a url", *secrets)
        resolved_token = _pick_text(
            api_token,
            None if profile is None else profile.api_token,
            "api_token",
            _OPEN_LIMIT,
            *secrets,
        )
        if not resolved_token:
            _raise_config_error("API token required", *secrets)
        if priority is not None:
            resolved_priority = _optional_priority(priority, *secrets)
        elif profile is not None and profile.priority is not None:
            resolved_priority = profile.priority
        else:
            resolved_priority = 0
        if resolved_priority is None:
            resolved_priority = 0
        return ResolvedSettings(
            user_key=_pick_text(
                user_key,
                None if profile is None else profile.user_key,
                "user_key",
                _OPEN_LIMIT,
                *secrets,
            ),
            api_token=resolved_token,
            title=_pick_text(
                title,
                None if profile is None else profile.title,
                "title",
                MAX_TITLE,
                *secrets,
            ),
            url=resolved_url,
            url_title=resolved_url_title,
            sound=_pick_text(
                sound,
                None if profile is None else profile.sound,
                "sound",
                _OPEN_LIMIT,
                *secrets,
            ),
            device=_pick_text(
                device,
                None if profile is None else profile.device,
                "device",
                _OPEN_LIMIT,
                *secrets,
            ),
            priority=resolved_priority,
            timeout=_pick_timeout(timeout, None if profile is None else profile.timeout, *secrets),
            retry=_pick_retry(retry, None if profile is None else profile.retry, *secrets),
            expire=_pick_expire(expire, None if profile is None else profile.expire, *secrets),
        )
    except ConfigError as exc:
        _reraise_config_error(exc, *cli_secrets, *yaml_secrets)


def _pick_text(
    cli_value: str | None,
    profile_value: str | None,
    field: str,
    limit: int,
    *secrets: str,
) -> str | None:
    chosen = cli_value if cli_value is not None else profile_value
    if chosen is None:
        return None
    try:
        return require_text(chosen, field, limit)
    except ValueError as exc:
        error, cause = _config_error_from(exc, *secrets)
        raise error from cause


def _pick_timeout(cli_value: float | None, profile_value: float | None, *secrets: str) -> float:
    if cli_value is not None:
        try:
            return require_timeout(cli_value)
        except ValueError as exc:
            error, cause = _config_error_from(exc, *secrets)
            raise error from cause
    if profile_value is not None:
        return profile_value
    return DEFAULT_TIMEOUT


def _pick_retry(cli_value: int | None, profile_value: int | None, *secrets: str) -> int:
    if cli_value is not None:
        parsed = _optional_retry(cli_value, *secrets)
        return 30 if parsed is None else parsed
    if profile_value is not None:
        return profile_value
    return 30


def _pick_expire(cli_value: int | None, profile_value: int | None, *secrets: str) -> int:
    if cli_value is not None:
        parsed = _optional_expire(cli_value, *secrets)
        return 3600 if parsed is None else parsed
    if profile_value is not None:
        return profile_value
    return 3600


def _profiles(loaded: object, config_path: Path) -> dict[object, object]:
    if not isinstance(loaded, dict):
        raise ConfigError(f"invalid config file: {config_path}")
    unknown = sorted(str(key) for key in loaded if key != "profiles")
    if unknown:
        raise ConfigError(f"unknown config setting: {', '.join(unknown)}")
    profiles = loaded.get("profiles")
    if not isinstance(profiles, dict) or not profiles:
        raise ConfigError("config file must define profiles")
    for name in profiles:
        if not isinstance(name, str) or not name:
            raise ConfigError("profile names must be strings")
    return profiles


def _optional_text(value: object, field: str, limit: int, *secrets: str) -> str | None:
    if value is None:
        return None
    try:
        return require_text(value, field, limit)
    except ValueError as exc:
        error, cause = _config_error_from(exc, *secrets)
        raise error from cause


def _optional_priority(value: object, *secrets: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value not in _PRIORITIES:
        _raise_config_error("priority must be -2, -1, 0, or 1", *secrets)
    return value


def _optional_timeout(value: object, *secrets: str) -> float | None:
    if value is None:
        return None
    try:
        return require_timeout(value)
    except ValueError as exc:
        error, cause = _config_error_from(exc, *secrets)
        raise error from cause


def _optional_retry(value: object, *secrets: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 30:
        _raise_config_error("retry must be an integer greater than or equal to 30", *secrets)
    return value


def _optional_expire(value: object, *secrets: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 1 or value > 10800:
        _raise_config_error("expire must be an integer from 1 through 10800", *secrets)
    return value


def _read_config(config_path: Path) -> tuple[object, tuple[str, ...]]:
    try:
        loaded: object = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"invalid config file: {config_path}") from exc
    return loaded, _collect_yaml_secrets(loaded)


def _collect_yaml_secrets(loaded: object) -> tuple[str, ...]:
    if not isinstance(loaded, dict):
        return ()
    profiles = loaded.get("profiles")
    if not isinstance(profiles, dict):
        return ()
    seen: set[str] = set()
    result: list[str] = []
    for profile_data in profiles.values():
        if not isinstance(profile_data, dict):
            continue
        for key in ("api_token", "user_key"):
            value = profile_data.get(key)
            if isinstance(value, str) and value and value not in seen:
                seen.add(value)
                result.append(value)
    return tuple(result)


def _profile_secrets(raw: dict[object, object]) -> tuple[str, ...]:
    secrets: list[str] = []
    for key in ("api_token", "user_key"):
        value = raw.get(key)
        if isinstance(value, str) and value:
            secrets.append(value)
    return tuple(secrets)


def _cli_secrets(*, user_key: str | None, api_token: str | None) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in (api_token, user_key):
        if isinstance(value, str) and value and value not in seen:
            seen.add(value)
            result.append(value)
    return tuple(result)


def _settings_secrets(
    profile: Profile | None,
    *,
    user_key: str | None,
    api_token: str | None,
) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in (api_token, user_key):
        if isinstance(value, str) and value and value not in seen:
            seen.add(value)
            result.append(value)
    if profile is not None:
        for value in (profile.api_token, profile.user_key):
            if isinstance(value, str) and value and value not in seen:
                seen.add(value)
                result.append(value)
    return tuple(result)


def _redact_secrets(text: str, *secrets: str) -> str:
    for secret in sorted((secret for secret in secrets if secret), key=len, reverse=True):
        text = text.replace(secret, "[redacted]")
    return text


def _raise_config_error(message: str, *secrets: str) -> NoReturn:
    redacted = _redact_secrets(message, *secrets)
    if redacted != message:
        raise ConfigError(redacted) from None
    raise ConfigError(message)


def _config_error_from(
    exc: BaseException,
    *secrets: str,
) -> tuple[ConfigError, BaseException | None]:
    message = str(exc)
    redacted = _redact_secrets(message, *secrets)
    if redacted != message:
        return ConfigError(redacted), None
    return ConfigError(message), exc


def _reraise_config_error(exc: ConfigError, *secrets: str) -> NoReturn:
    message = str(exc)
    redacted = _redact_secrets(message, *secrets)
    if redacted != message:
        raise ConfigError(redacted) from None
    raise exc
