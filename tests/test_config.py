"""Profile loading."""

from __future__ import annotations

from pathlib import Path

import pytest

from lupaxa.pushit.config import ConfigError, default_config_path, load_profile, resolve_settings

TOKEN = "app-token-value"
USER = "user-key-value"


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def test_default_path_is_home_dotfile() -> None:
    assert default_config_path() == Path.home() / ".pushit.yml"


def test_load_profile_reads_known_fields(tmp_path: Path) -> None:
    path = tmp_path / "pushit.yml"
    _write(
        path,
        """
profiles:
  alerts:
    user_key: user-key-value
    api_token: app-token-value
    title: pushit
    url: https://example.com
    url_title: Open
    sound: pushover
    device: phone
    priority: 1
    timeout: 15
    retry: 45
    expire: 600
""",
    )
    profile = load_profile("alerts", path)
    assert profile.user_key == USER
    assert profile.api_token == TOKEN
    assert profile.priority == 1
    assert profile.retry == 45
    assert profile.expire == 600


def test_unknown_key_and_bad_types(tmp_path: Path) -> None:
    path = tmp_path / "pushit.yml"
    _write(path, "profiles:\n  alerts:\n    api_token: app-token-value\n    extra: 1\n")
    with pytest.raises(ConfigError, match="unknown profile setting"):
        load_profile("alerts", path)
    _write(path, "profiles:\n  alerts:\n    priority: true\n")
    with pytest.raises(ConfigError, match="priority"):
        load_profile("alerts", path)
    _write(path, "profiles:\n  alerts:\n    priority: 2\n")
    with pytest.raises(ConfigError, match="priority"):
        load_profile("alerts", path)
    _write(path, "profiles:\n  alerts:\n    retry: 10\n")
    with pytest.raises(ConfigError, match="retry"):
        load_profile("alerts", path)


def test_missing_file_and_config_without_profile(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="config file not found"):
        load_profile("alerts", tmp_path / "missing.yml")
    with pytest.raises(ConfigError, match="--profile is required"):
        resolve_settings(
            profile_name=None,
            config_path=tmp_path / "pushit.yml",
            user_key=None,
            api_token=TOKEN,
            title=None,
            url=None,
            url_title=None,
            sound=None,
            device=None,
            priority=None,
            timeout=None,
            retry=None,
            expire=None,
        )


def test_flags_override_profile(tmp_path: Path) -> None:
    path = tmp_path / "pushit.yml"
    _write(
        path,
        """
profiles:
  alerts:
    user_key: from-profile
    api_token: from-profile-token
    title: from-profile
    priority: 1
    retry: 45
    expire: 90
    timeout: 15
""",
    )
    settings = resolve_settings(
        profile_name="alerts",
        config_path=path,
        user_key=USER,
        api_token=TOKEN,
        title="from-cli",
        url=None,
        url_title=None,
        sound=None,
        device=None,
        priority=None,
        timeout=None,
        retry=None,
        expire=None,
    )
    assert settings.user_key == USER
    assert settings.api_token == TOKEN
    assert settings.title == "from-cli"
    assert settings.priority == 1
    assert settings.retry == 45
    assert settings.expire == 90
    assert settings.timeout == 15.0


def test_defaults_and_url_title_rule() -> None:
    settings = resolve_settings(
        profile_name=None,
        config_path=None,
        user_key=USER,
        api_token=TOKEN,
        title=None,
        url=None,
        url_title=None,
        sound=None,
        device=None,
        priority=None,
        timeout=None,
        retry=None,
        expire=None,
    )
    assert settings.priority == 0
    assert settings.timeout == 10.0
    assert settings.retry == 30
    assert settings.expire == 3600
    with pytest.raises(ConfigError, match="API token required"):
        resolve_settings(
            profile_name=None,
            config_path=None,
            user_key=USER,
            api_token=None,
            title=None,
            url=None,
            url_title=None,
            sound=None,
            device=None,
            priority=None,
            timeout=None,
            retry=None,
            expire=None,
        )
    with pytest.raises(ConfigError, match="url_title requires a url"):
        resolve_settings(
            profile_name=None,
            config_path=None,
            user_key=USER,
            api_token=TOKEN,
            title=None,
            url=None,
            url_title="Open",
            sound=None,
            device=None,
            priority=None,
            timeout=None,
            retry=None,
            expire=None,
        )


def test_api_token_substring_redacted_from_priority_error(tmp_path: Path) -> None:
    path = tmp_path / "pushit.yml"
    _write(
        path,
        """
profiles:
  alerts:
    api_token: priority
    priority: true
""",
    )
    with pytest.raises(ConfigError) as exc_info:
        load_profile("alerts", path)
    message = str(exc_info.value)
    assert "[redacted]" in message
    assert "priority" not in message
    assert exc_info.value.__cause__ is None


def test_unknown_top_level_key_redacts_profile_api_token(tmp_path: Path) -> None:
    path = tmp_path / "pushit.yml"
    _write(
        path,
        """
priority-key: 1
profiles:
  alerts:
    api_token: priority-key
""",
    )
    with pytest.raises(ConfigError) as exc_info:
        load_profile("alerts", path)
    message = str(exc_info.value)
    assert "priority-key" not in message
    assert exc_info.value.__cause__ is None


def test_resolve_settings_redacts_cli_token_when_profile_missing(tmp_path: Path) -> None:
    path = tmp_path / "pushit.yml"
    _write(
        path,
        """
profiles:
  alerts:
    api_token: from-profile
""",
    )
    with pytest.raises(ConfigError) as exc_info:
        resolve_settings(
            profile_name="priority-key",
            config_path=path,
            user_key=None,
            api_token="priority-key",
            title=None,
            url=None,
            url_title=None,
            sound=None,
            device=None,
            priority=None,
            timeout=None,
            retry=None,
            expire=None,
        )
    message = str(exc_info.value)
    assert "priority-key" not in message
    assert exc_info.value.__cause__ is None


def test_longer_secret_redacted_before_shorter_substring(tmp_path: Path) -> None:
    path = tmp_path / "pushit.yml"
    _write(
        path,
        """
priority: 1
priority-key: 2
profiles:
  alerts:
    api_token: priority-key
    user_key: priority
""",
    )
    with pytest.raises(ConfigError) as exc_info:
        load_profile("alerts", path)
    message = str(exc_info.value)
    assert "-key" not in message
    assert "priority" not in message
    assert "[redacted]" in message
    assert exc_info.value.__cause__ is None


def test_empty_cli_user_key_does_not_redact_api_token_required() -> None:
    with pytest.raises(ConfigError, match="^API token required$") as exc_info:
        resolve_settings(
            profile_name=None,
            config_path=None,
            user_key="",
            api_token=None,
            title=None,
            url=None,
            url_title=None,
            sound=None,
            device=None,
            priority=None,
            timeout=None,
            retry=None,
            expire=None,
        )
    assert str(exc_info.value) == "API token required"
    assert exc_info.value.__cause__ is None
