"""Pushover client."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from lupaxa.pushit.client import MESSAGES_URL, SOUNDS_URL, Pushit

TOKEN = "app-token-value"
USER = "user-key-value"
GROUP = "group-key-value"


def _response(
    status: int = 200,
    payload: dict[str, object] | None = None,
    text: str | None = None,
) -> MagicMock:
    response = MagicMock()
    response.status_code = status
    body = {"status": 1, "request": "req"} if payload is None else payload
    response.json.return_value = body
    response.text = json.dumps(body) if text is None else text
    return response


def test_send_omits_unset_fields() -> None:
    response = _response()
    with patch("lupaxa.pushit.client.requests.post", return_value=response) as post:
        Pushit(TOKEN, USER).send_message("hello")
    data = post.call_args.kwargs["data"]
    assert data["token"] == TOKEN
    assert data["user"] == USER
    assert data["message"] == "hello"
    assert data["priority"] == "0"
    assert "title" not in data
    assert "url" not in data
    assert "url_title" not in data
    assert "sound" not in data
    assert "device" not in data
    assert "retry" not in data
    assert "expire" not in data
    assert "files" not in post.call_args.kwargs
    assert post.call_args.args[0] == MESSAGES_URL
    assert post.call_args.kwargs["allow_redirects"] is False


def test_emergency_and_group_share_one_post() -> None:
    response = _response(payload={"status": 1, "request": "req", "receipt": "receipt-id"})
    with patch("lupaxa.pushit.client.requests.post", return_value=response) as post:
        body = Pushit(TOKEN, USER).send_message(
            "down",
            priority=2,
            retry=45,
            expire=600,
            group_key=GROUP,
        )
    data = post.call_args.kwargs["data"]
    assert data["user"] == GROUP
    assert data["priority"] == "2"
    assert data["retry"] == "45"
    assert data["expire"] == "600"
    assert body["receipt"] == "receipt-id"


def test_retry_without_emergency_raises() -> None:
    with pytest.raises(ValueError, match="require emergency priority"):
        Pushit(TOKEN, USER).send_message("hello", retry=30)


def test_emergency_without_retry_raises() -> None:
    with pytest.raises(ValueError, match="required for emergency"):
        Pushit(TOKEN, USER).send_message("hello", priority=2, expire=60)


def test_limits_and_url_title() -> None:
    client = Pushit(TOKEN, USER)
    with pytest.raises(ValueError, match="1024"):
        client.send_message("x" * 1025)
    with pytest.raises(ValueError, match="250"):
        client.send_message("hi", title="t" * 251)
    with pytest.raises(ValueError, match="512"):
        client.send_message("hi", url="u" * 513)
    with pytest.raises(ValueError, match="100"):
        client.send_message("hi", url="https://example.com", url_title="n" * 101)
    with pytest.raises(ValueError, match="url_title requires a url"):
        client.send_message("hi", url_title="Open")
    with pytest.raises(ValueError, match="priority"):
        client.send_message("hi", priority=3)
    with pytest.raises(ValueError, match="30"):
        client.send_message("hi", priority=2, retry=29, expire=60)
    with pytest.raises(ValueError, match="10800"):
        client.send_message("hi", priority=2, retry=30, expire=10801)


def test_attachment_multipart(tmp_path: Path) -> None:
    path = tmp_path / "shot.png"
    path.write_bytes(b"png")
    response = _response()
    with patch("lupaxa.pushit.client.requests.post", return_value=response) as post:
        Pushit(TOKEN, USER).send_message("see", attachment=str(path))
    assert "attachment" in post.call_args.kwargs["files"]


def test_missing_and_oversized_attachment(tmp_path: Path) -> None:
    client = Pushit(TOKEN, USER)
    with pytest.raises(ValueError, match="file not found"):
        client.send_message("see", attachment=str(tmp_path / "missing.png"))
    huge = tmp_path / "huge.png"
    huge.write_bytes(b"x" * (5_242_881))
    with pytest.raises(ValueError, match="5242880"):
        client.send_message("see", attachment=str(huge))


def test_sounds_get_uses_token_only() -> None:
    response = _response(payload={"status": 1, "sounds": {"pushover": "Pushover"}})
    with patch("lupaxa.pushit.client.requests.get", return_value=response) as get:
        body = Pushit(TOKEN).list_sounds()
    assert get.call_args.args[0] == SOUNDS_URL
    assert get.call_args.kwargs["params"] == {"token": TOKEN}
    assert body["sounds"] == {"pushover": "Pushover"}


def test_api_errors_omit_secrets() -> None:
    response = _response(
        status=400,
        payload={"status": 0, "errors": ["user identifier is invalid", "bad token field"]},
    )
    with (
        patch("lupaxa.pushit.client.requests.post", return_value=response),
        pytest.raises(ValueError, match="user identifier is invalid; bad token field") as exc,
    ):
        Pushit(TOKEN, USER).send_message("hi")
    assert TOKEN not in str(exc.value)
    assert USER not in str(exc.value)


def test_api_errors_redact_secrets_in_body() -> None:
    response = _response(
        status=400,
        payload={
            "status": 0,
            "errors": [f"invalid token {TOKEN}", f"invalid user {USER}"],
        },
    )
    with (
        patch("lupaxa.pushit.client.requests.post", return_value=response),
        pytest.raises(ValueError, match=r"invalid token \[redacted\]") as exc,
    ):
        Pushit(TOKEN, USER).send_message("hi")
    message = str(exc.value)
    assert "[redacted]" in message
    assert TOKEN not in message
    assert USER not in message


def test_missing_attachment_redacts_token_path() -> None:
    with pytest.raises(ValueError, match="file not found") as exc:
        Pushit(TOKEN, USER).send_message("see", attachment=TOKEN)
    assert TOKEN not in str(exc.value)


def test_missing_attachment_redacts_group_key_path() -> None:
    with pytest.raises(ValueError, match="file not found") as exc:
        Pushit(TOKEN, USER).send_message("see", group_key=GROUP, attachment=GROUP)
    assert GROUP not in str(exc.value)


def test_non_json_error_uses_body() -> None:
    response = MagicMock()
    response.status_code = 500
    response.json.side_effect = ValueError("bad json")
    response.text = "boom"
    with (
        patch("lupaxa.pushit.client.requests.post", return_value=response),
        pytest.raises(ValueError, match="boom"),
    ):
        Pushit(TOKEN, USER).send_message("hi")


def test_request_exception_propagates() -> None:
    with (
        patch(
            "lupaxa.pushit.client.requests.post",
            side_effect=requests.ConnectionError("down"),
        ),
        pytest.raises(requests.ConnectionError),
    ):
        Pushit(TOKEN, USER).send_message("hi")


def test_missing_recipient() -> None:
    with pytest.raises(ValueError, match="user key required"):
        Pushit(TOKEN).send_message("hi")


def test_validation_error_redacts_token_used_as_word() -> None:
    client = Pushit("priority", USER)
    with pytest.raises(ValueError, match=r"\[redacted\]") as exc:
        client.send_message("hi", priority=3)
    assert "priority" not in str(exc.value)
    assert USER not in str(exc.value)
    assert exc.value.__cause__ is None


def test_init_validation_error_redacts_secrets() -> None:
    with pytest.raises(ValueError, match=r"\[redacted\]") as exc:
        Pushit(TOKEN, "number", timeout="no")  # type: ignore[arg-type]
    message = str(exc.value)
    assert "number" not in message
    assert exc.value.__cause__ is None


def test_list_sounds_api_error_redacts_token() -> None:
    response = _response(
        status=400,
        payload={"status": 0, "errors": [f"invalid token {TOKEN}"]},
    )
    with (
        patch("lupaxa.pushit.client.requests.get", return_value=response),
        pytest.raises(ValueError, match=r"\[redacted\]") as exc,
    ):
        Pushit(TOKEN).list_sounds()
    message = str(exc.value)
    assert TOKEN not in message
    assert "[redacted]" in message
