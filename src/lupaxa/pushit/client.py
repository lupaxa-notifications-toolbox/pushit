"""Pushover API client."""

from __future__ import annotations

import math
from pathlib import Path
from typing import NoReturn, cast

import requests

DEFAULT_TIMEOUT = 10.0
MESSAGES_URL = "https://api.pushover.net/1/messages.json"
SOUNDS_URL = "https://api.pushover.net/1/sounds.json"
MAX_MESSAGE = 1024
MAX_TITLE = 250
MAX_URL = 512
MAX_URL_TITLE = 100
MAX_ATTACHMENT_BYTES = 5_242_880
_PRIORITIES = frozenset({-2, -1, 0, 1, 2})
_OPEN_LIMIT = 10**6


def require_timeout(timeout: object) -> float:
    """Return ``timeout`` when it is finite and greater than 0."""
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
        raise ValueError("timeout must be a number")
    number = float(timeout)
    if not math.isfinite(number) or number <= 0:
        raise ValueError("timeout must be greater than 0")
    return number


def require_text(value: object, field: str, limit: int) -> str:
    """Return ``value`` when it is a non-empty string within ``limit``."""
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty string")
    if len(value) > limit:
        raise ValueError(f"{field} must be at most {limit} characters")
    return value


class Pushit:
    """Send one Pushover message and list notification sounds."""

    def __init__(
        self,
        api_token: str,
        user_key: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        """Store the application token, optional user key, and timeout."""
        secrets: tuple[str, ...] = ()
        if isinstance(api_token, str) and api_token:
            secrets = (api_token,)
        if isinstance(user_key, str) and user_key:
            secrets = (*secrets, user_key)
        try:
            if not isinstance(api_token, str) or not api_token:
                raise ValueError("API token required")
            if user_key is not None:
                require_text(user_key, "user_key", _OPEN_LIMIT)
            self.api_token = api_token
            self.user_key = user_key
            self.timeout = require_timeout(timeout)
        except requests.RequestException:
            raise
        except ValueError as exc:
            _reraise_redacted(exc, *secrets)

    def send_message(
        self,
        message: str,
        *,
        title: str | None = None,
        url: str | None = None,
        url_title: str | None = None,
        priority: int = 0,
        sound: str | None = None,
        device: str | None = None,
        attachment: str | None = None,
        group_key: str | None = None,
        retry: int | None = None,
        expire: int | None = None,
    ) -> dict[str, object]:
        """POST one message and return the JSON body."""
        secrets: tuple[str, ...] = (self.api_token,)
        if self.user_key is not None:
            secrets = (*secrets, self.user_key)
        if group_key is not None:
            secrets = (*secrets, group_key)
        try:
            body = require_text(message, "message", MAX_MESSAGE)
            _check_priority(priority)
            _check_emergency(priority, retry, expire)
            payload: dict[str, object] = {
                "token": self.api_token,
                "user": _recipient(group_key, self.user_key),
                "message": body,
                "priority": priority,
            }
            _put_text(payload, "title", title, MAX_TITLE)
            _put_text(payload, "url", url, MAX_URL)
            if url_title is not None:
                if url is None:
                    raise ValueError("url_title requires a url")
                _put_text(payload, "url_title", url_title, MAX_URL_TITLE)
            _put_text(payload, "sound", sound, _OPEN_LIMIT)
            _put_text(payload, "device", device, _OPEN_LIMIT)
            if priority == 2:
                payload["retry"] = retry
                payload["expire"] = expire
            form = {key: str(value) for key, value in payload.items()}
            if attachment is None:
                response = requests.post(
                    MESSAGES_URL,
                    data=form,
                    timeout=self.timeout,
                    allow_redirects=False,
                )
            else:
                path = _attachment_path(attachment, *secrets)
                with path.open("rb") as handle:
                    response = requests.post(
                        MESSAGES_URL,
                        data=form,
                        files={"attachment": (path.name, handle)},
                        timeout=self.timeout,
                        allow_redirects=False,
                    )
            return _parse_response(response, *secrets)
        except requests.RequestException:
            raise
        except ValueError as exc:
            _reraise_redacted(exc, *secrets)

    def list_sounds(self) -> dict[str, object]:
        """GET the sound catalogue and return the JSON body."""
        secrets: tuple[str, ...] = (self.api_token,)
        if self.user_key is not None:
            secrets = (*secrets, self.user_key)
        try:
            response = requests.get(
                SOUNDS_URL,
                params={"token": self.api_token},
                timeout=self.timeout,
                allow_redirects=False,
            )
            return _parse_response(response, *secrets)
        except requests.RequestException:
            raise
        except ValueError as exc:
            _reraise_redacted(exc, *secrets)


def _recipient(group_key: str | None, user_key: str | None) -> str:
    if group_key is not None:
        return require_text(group_key, "group_key", _OPEN_LIMIT)
    if user_key is None:
        raise ValueError("user key required")
    return user_key


def _check_priority(priority: object) -> None:
    if isinstance(priority, bool) or not isinstance(priority, int) or priority not in _PRIORITIES:
        raise ValueError("priority must be -2, -1, 0, 1, or 2")


def _check_emergency(priority: int, retry: object, expire: object) -> None:
    if priority != 2:
        if retry is not None or expire is not None:
            raise ValueError("retry and expire require emergency priority")
        return
    if retry is None or expire is None:
        raise ValueError("retry and expire are required for emergency priority")
    if isinstance(retry, bool) or not isinstance(retry, int) or retry < 30:
        raise ValueError("retry must be an integer greater than or equal to 30")
    if isinstance(expire, bool) or not isinstance(expire, int) or expire < 1 or expire > 10800:
        raise ValueError("expire must be an integer from 1 through 10800")


def _put_text(payload: dict[str, object], field: str, value: str | None, limit: int) -> None:
    if value is None:
        return
    payload[field] = require_text(value, field, limit)


def _redact_secrets(text: str, *secrets: str) -> str:
    for secret in sorted((secret for secret in secrets if secret), key=len, reverse=True):
        text = text.replace(secret, "[redacted]")
    return text


def _reraise_redacted(exc: ValueError, *secrets: str) -> NoReturn:
    raise ValueError(_redact_secrets(str(exc), *secrets)) from None


def _attachment_path(path_text: str, *secrets: str) -> Path:
    path = Path(path_text)
    if not path.is_file():
        raise ValueError(_redact_secrets(f"file not found: {path_text}", *secrets))
    if path.stat().st_size > MAX_ATTACHMENT_BYTES:
        raise ValueError("attachment must be at most 5242880 bytes")
    return path


def _parse_response(response: requests.Response, *secrets: str) -> dict[str, object]:
    if response.status_code < 200 or response.status_code >= 300:
        raise ValueError(_redact_secrets(_error_text(response), *secrets))
    try:
        loaded = response.json()
    except ValueError as exc:
        raise ValueError(_redact_secrets(response.text, *secrets)) from exc
    if not isinstance(loaded, dict) or loaded.get("status") != 1:
        raise ValueError(_redact_secrets(_error_text(response), *secrets))
    return cast("dict[str, object]", loaded)


def _error_text(response: requests.Response) -> str:
    try:
        loaded = response.json()
    except ValueError:
        return response.text
    if isinstance(loaded, dict):
        errors = loaded.get("errors")
        if isinstance(errors, list) and errors:
            return "; ".join(str(item) for item in errors)
    return response.text
