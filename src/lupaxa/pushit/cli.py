"""Command-line interface for Pushit."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import NoReturn

import requests

from .client import DEFAULT_TIMEOUT, Pushit, require_timeout
from .config import ConfigError, ResolvedSettings, resolve_settings
from .version import get_version

_SEND_FLAGS = (
    "title",
    "url",
    "url_title",
    "priority",
    "sound",
    "device",
    "attachment",
    "group",
)


def _priority(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("priority must be -2, -1, 0, or 1") from exc
    if number not in (-2, -1, 0, 1):
        raise argparse.ArgumentTypeError("priority must be -2, -1, 0, or 1")
    return number


def _retry(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "retry must be an integer greater than or equal to 30"
        ) from exc
    if number < 30:
        raise argparse.ArgumentTypeError("retry must be an integer greater than or equal to 30")
    return number


def _expire(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expire must be an integer from 1 through 10800") from exc
    if number < 1 or number > 10800:
        raise argparse.ArgumentTypeError("expire must be an integer from 1 through 10800")
    return number


def _positive_timeout(value: str) -> float:
    try:
        return require_timeout(float(value))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _exit_code(exc: SystemExit) -> int:
    code = exc.code
    if code is None:
        return 0
    return code if isinstance(code, int) else 1


def _program_name(argv0: str) -> str:
    name = os.path.basename(argv0)
    if name == "__main__.py" or name.startswith("pytest"):
        return "pushit"
    return name


def _collect_secrets(
    *,
    user_key: str | None = None,
    api_token: str | None = None,
    group_key: str | None = None,
    settings: ResolvedSettings | None = None,
) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in (
        api_token,
        user_key,
        group_key,
        None if settings is None else settings.api_token,
        None if settings is None else settings.user_key,
    ):
        if isinstance(value, str) and value and value not in seen:
            seen.add(value)
            result.append(value)
    return tuple(result)


def _redact_secrets(message: str, *secrets: str) -> str:
    for secret in sorted((secret for secret in secrets if secret), key=len, reverse=True):
        message = message.replace(secret, "[redacted]")
    return message


def _print_error(message: str, *secrets: str) -> None:
    redacted = _redact_secrets(str(message), *secrets)
    print(f"{_program_name(sys.argv[0])}: {redacted}", file=sys.stderr)


_SECRET_ARG_FLAGS = frozenset({"--token", "--user", "--group"})


def _collect_argv_secrets(argv: list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    index = 0
    while index < len(argv):
        arg = argv[index]
        flag: str | None = None
        value: str | None = None
        if arg in _SECRET_ARG_FLAGS:
            flag = arg
            if index + 1 < len(argv):
                value = argv[index + 1]
                index += 1
            else:
                value = ""
        else:
            for secret_flag in _SECRET_ARG_FLAGS:
                prefix = f"{secret_flag}="
                if arg.startswith(prefix):
                    flag = secret_flag
                    value = arg[len(prefix) :]
                    break
        if flag is not None and value and value not in seen:
            seen.add(value)
            result.append(value)
        index += 1
    return tuple(result)


class RedactingArgumentParser(argparse.ArgumentParser):
    """Argument parser that redacts secret values from usage errors."""

    def __init__(
        self,
        *,
        secrets: tuple[str, ...] = (),
        description: str | None = None,
    ) -> None:
        super().__init__(description=description)
        self._secrets = secrets

    def error(self, message: str) -> NoReturn:
        """Write a usage error message with secrets redacted."""
        redacted = _redact_secrets(message, *self._secrets)
        self.exit(2, f"{self.prog}: error: {redacted}\n")


def build_parser(*, secrets: tuple[str, ...] = ()) -> RedactingArgumentParser:
    """Build the ``pushit`` argument parser."""
    parser = RedactingArgumentParser(description="Send a Pushover notification.", secrets=secrets)
    parser.add_argument("--user", default=None, help="Pushover user key")
    parser.add_argument("--token", default=None, help="Application API token")
    parser.add_argument("-p", "--profile", default=None, metavar="NAME", help="Profile name")
    parser.add_argument(
        "--config",
        default=None,
        metavar="PATH",
        help="Config file (default: ~/.pushit.yml)",
    )
    parser.add_argument("-t", "--text", default=None, help="Message content")
    parser.add_argument("--title", default=None, help="Message title")
    parser.add_argument("--url", default=None, help="Supplementary URL")
    parser.add_argument("--url-title", default=None, help="Title for the supplementary URL")
    parser.add_argument("--sound", default=None, help="Sound name")
    parser.add_argument("--device", default=None, help="Device name or comma-separated names")
    parser.add_argument("--attachment", default=None, help="Image file to attach")
    parser.add_argument("--group", default=None, help="Group key")
    parser.add_argument("--priority", type=_priority, default=None, help="Priority -2, -1, 0, or 1")
    parser.add_argument("--emergency", action="store_true", help="Send at emergency priority")
    parser.add_argument(
        "--retry",
        type=_retry,
        default=None,
        help="Seconds between emergency retries",
    )
    parser.add_argument(
        "--expire",
        type=_expire,
        default=None,
        help="Emergency lifetime in seconds",
    )
    parser.add_argument(
        "-T",
        "--timeout",
        type=_positive_timeout,
        default=None,
        metavar="SECONDS",
        help=f"Request timeout in seconds (default: {DEFAULT_TIMEOUT:g})",
    )
    parser.add_argument("--sounds", action="store_true", help="List sound names")
    parser.add_argument("--version", action="version", version=get_version())
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return a process exit code."""
    argv_list = list(sys.argv[1:] if argv is None else argv)
    argv_secrets = _collect_argv_secrets(argv_list)
    parser = build_parser(secrets=argv_secrets)
    try:
        args = parser.parse_args(argv_list)
    except SystemExit as exc:
        return _exit_code(exc)
    send_values = [getattr(args, name) for name in _SEND_FLAGS]
    sounds_with_send = args.text is not None or args.emergency or args.retry is not None
    sounds_with_send = sounds_with_send or args.expire is not None
    sounds_with_send = sounds_with_send or any(value is not None for value in send_values)
    try:
        if args.sounds and sounds_with_send:
            parser.error("--sounds cannot be combined with a send")
        if args.text is None and not args.sounds:
            parser.error("one of --text or --sounds is required")
        if args.emergency and args.priority is not None:
            parser.error("--priority cannot be combined with --emergency")
        if not args.emergency and (args.retry is not None or args.expire is not None):
            parser.error("--retry and --expire require --emergency")
    except SystemExit as exc:
        return _exit_code(exc)
    config_path = Path(args.config).expanduser() if args.config else None
    settings: ResolvedSettings | None = None
    secrets = _collect_secrets(
        user_key=args.user,
        api_token=args.token,
        group_key=args.group,
    )
    try:
        settings = resolve_settings(
            profile_name=args.profile,
            config_path=config_path,
            user_key=args.user,
            api_token=args.token,
            title=args.title,
            url=args.url,
            url_title=args.url_title,
            sound=args.sound,
            device=args.device,
            priority=args.priority,
            timeout=args.timeout,
            retry=args.retry,
            expire=args.expire,
        )
        secrets = _collect_secrets(
            user_key=args.user,
            api_token=args.token,
            group_key=args.group,
            settings=settings,
        )
        if not args.sounds and args.group is None and not settings.user_key:
            raise ConfigError("user key required")
        client = Pushit(settings.api_token, user_key=settings.user_key, timeout=settings.timeout)
        if args.sounds:
            body = client.list_sounds()
            sounds = body.get("sounds")
            if not isinstance(sounds, dict):
                raise ValueError("sounds list missing")
            for name in sorted(str(key) for key in sounds):
                print(name)
            return 0
        if args.text is None:
            raise ValueError("message must be a non-empty string")
        client.send_message(
            args.text,
            title=settings.title,
            url=settings.url,
            url_title=settings.url_title,
            priority=2 if args.emergency else settings.priority,
            sound=settings.sound,
            device=settings.device,
            attachment=args.attachment,
            group_key=args.group,
            retry=settings.retry if args.emergency else None,
            expire=settings.expire if args.emergency else None,
        )
    except ConfigError as exc:
        _print_error(str(exc), *secrets)
        return 2
    except (ValueError, requests.RequestException) as exc:
        _print_error(str(exc), *secrets)
        return 1
    return 0
