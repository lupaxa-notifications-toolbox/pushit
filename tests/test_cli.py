"""CLI entrypoint."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from lupaxa.pushit.cli import main
from lupaxa.pushit.version import get_version

TOKEN = "app-token-value"
USER = "user-key-value"
_BASE = ["--user", USER, "--token", TOKEN]


def test_help_and_version(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--help"]) == 0
    assert "--text" in capsys.readouterr().out
    assert main(["--version"]) == 0
    assert get_version() in capsys.readouterr().out


def test_missing_token_and_recipient_and_mode(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--user", USER, "--text", "hi"]) == 2
    err = capsys.readouterr().err
    assert "API token required" in err
    assert "[redacted]" not in err
    assert main(["--token", TOKEN, "--text", "hi"]) == 2
    assert "user key required" in capsys.readouterr().err
    assert main(_BASE) == 2


def test_sounds_excludes_send() -> None:
    assert main([*_BASE, "--sounds", "--text", "hi"]) == 2
    assert main([*_BASE, "--sounds", "--emergency"]) == 2
    assert main([*_BASE, "--priority", "1", "--emergency", "--text", "hi"]) == 2
    assert main([*_BASE, "--retry", "30", "--text", "hi"]) == 2


def test_url_title_without_url() -> None:
    assert main([*_BASE, "--text", "hi", "--url-title", "Open"]) == 2


def test_emergency_group_dispatch() -> None:
    client = MagicMock()
    with patch("lupaxa.pushit.cli.Pushit", return_value=client):
        assert main([*_BASE, "--text", "down", "--emergency", "--group", "group-key"]) == 0
    client.send_message.assert_called_once_with(
        "down",
        title=None,
        url=None,
        url_title=None,
        priority=2,
        sound=None,
        device=None,
        attachment=None,
        group_key="group-key",
        retry=30,
        expire=3600,
    )


def test_profile_priority_ignored_for_emergency(tmp_path: Path) -> None:
    path = tmp_path / "pushit.yml"
    path.write_text(
        "profiles:\n  alerts:\n    user_key: user-key-value\n"
        "    api_token: app-token-value\n    priority: 1\n    retry: 45\n    expire: 90\n",
        encoding="utf-8",
    )
    client = MagicMock()
    with patch("lupaxa.pushit.cli.Pushit", return_value=client):
        assert main(["-p", "alerts", "--config", str(path), "--text", "down", "--emergency"]) == 0
    kwargs = client.send_message.call_args.kwargs
    assert kwargs["priority"] == 2
    assert kwargs["retry"] == 45
    assert kwargs["expire"] == 90


def test_profile_retry_not_sent_without_emergency(tmp_path: Path) -> None:
    path = tmp_path / "pushit.yml"
    path.write_text(
        "profiles:\n  alerts:\n    user_key: user-key-value\n"
        "    api_token: app-token-value\n    retry: 45\n",
        encoding="utf-8",
    )
    client = MagicMock()
    with patch("lupaxa.pushit.cli.Pushit", return_value=client):
        assert main(["-p", "alerts", "--config", str(path), "--text", "hi"]) == 0
    assert client.send_message.call_args.kwargs["retry"] is None
    assert client.send_message.call_args.kwargs["priority"] == 0


def test_sounds_prints_sorted_names(capsys: pytest.CaptureFixture[str]) -> None:
    client = MagicMock()
    client.list_sounds.return_value = {
        "status": 1,
        "sounds": {"bike": "Bike", "pushover": "Pushover"},
    }
    with patch("lupaxa.pushit.cli.Pushit", return_value=client):
        assert main(["--token", TOKEN, "--sounds"]) == 0
    assert capsys.readouterr().out == "bike\npushover\n"


def test_success_prints_nothing(capsys: pytest.CaptureFixture[str]) -> None:
    client = MagicMock()
    with patch("lupaxa.pushit.cli.Pushit", return_value=client):
        assert main([*_BASE, "--text", "hi"]) == 0
    assert capsys.readouterr().out == ""


def test_request_error_exits_one(capsys: pytest.CaptureFixture[str]) -> None:
    client = MagicMock()
    client.send_message.side_effect = ValueError("user identifier is invalid")
    with patch("lupaxa.pushit.cli.Pushit", return_value=client):
        assert main([*_BASE, "--text", "hi"]) == 1
    err = capsys.readouterr().err
    assert err.startswith("pushit:")
    assert TOKEN not in err
    assert USER not in err


def test_parse_error_redacts_token_in_type_message(capsys: pytest.CaptureFixture[str]) -> None:
    assert (
        main(
            [
                "--token",
                "priority",
                "--user",
                USER,
                "--timeout",
                "priority",
                "--text",
                "hi",
            ]
        )
        == 2
    )
    err = capsys.readouterr().err
    assert "[redacted]" in err
    assert "priority" not in err


def test_parse_error_redacts_longer_secret_before_shorter(
    capsys: pytest.CaptureFixture[str],
) -> None:
    longer = "group-key-value-long"
    shorter = "group-key-value"
    assert main(["--user", shorter, "--timeout", longer, "--text", "hi"]) == 2
    err = capsys.readouterr().err
    assert "[redacted]" in err
    assert longer not in err
    assert shorter not in err


def test_parse_error_redacts_hyphenated_token_value(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["--token", "-1", "--bogus", "-1"]) == 2
    err = capsys.readouterr().err
    assert "[redacted]" in err
    assert "-1" not in err


def test_parse_error_redacts_token_equals_hyphenated_value(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["--token=-1", "--bogus", "-1"]) == 2
    err = capsys.readouterr().err
    assert "[redacted]" in err
    assert "-1" not in err


def test_parse_error_redacts_priority_key_before_substrings(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert (
        main(
            [
                "--user",
                "priority",
                "--token",
                "priority-key",
                "--timeout",
                "priority-key",
            ]
        )
        == 2
    )
    err = capsys.readouterr().err
    assert "[redacted]" in err
    assert "priority-key" not in err
    assert "-key" not in err


def test_connection_error_redacts_token(capsys: pytest.CaptureFixture[str]) -> None:
    client = MagicMock()
    client.send_message.side_effect = requests.ConnectionError(
        f"HTTPSConnectionPool(host='api.pushover.net', token={TOKEN})"
    )
    with patch("lupaxa.pushit.cli.Pushit", return_value=client):
        assert main([*_BASE, "--text", "hi"]) == 1
    err = capsys.readouterr().err
    assert err.startswith("pushit:")
    assert TOKEN not in err
    assert "[redacted]" in err
