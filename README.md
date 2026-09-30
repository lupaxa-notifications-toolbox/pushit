<p align="center">
  <a href="https://github.com/lupaxa-notifications-toolbox">
    <img src="https://raw.githubusercontent.com/the-lupaxa-project/brand-assets/master/logos/organisations/notifications-toolbox/readme-logo.png" alt="Notifications Toolbox" />
  </a>
</p>

<h1 align="center">Pushit</h1>

Send Pushover notifications.

## Install

Pushit needs Python 3.13 or later, a Pushover user key, and an application API token.

```bash
pip install lupaxa-pushit
pushit --help
```

## CLI

```bash
pushit --user "$PUSHOVER_USER_KEY" --token "$PUSHOVER_API_TOKEN" --text "Hello"
pushit --profile alerts --text "Hello"
pushit -p alerts --config "$HOME/work/pushit.yml" --text "Disk full"
pushit --profile alerts --text "down" --emergency --group "$PUSHOVER_GROUP_KEY"
pushit --profile alerts --text "see" --title pushit --url https://example.com --url-title Open
pushit --profile alerts --text "see" --attachment report.png --sound pushover --device phone
pushit --token "$PUSHOVER_API_TOKEN" --sounds
python -m lupaxa.pushit --version
```

`--text` is required for a send. `--emergency` and `--group` may be
combined with it. `--priority` cannot be combined with `--emergency`.
`--retry` and `--expire` require `--emergency`. `--sounds` lists
sorted sound names, one per line, and cannot be combined with a send.

A successful send prints nothing. The `$PUSHOVER_*` names are shell
variables expanded before pushit runs. Pushit does not read environment
variables. A command-line value overrides the same profile field.
`--group` replaces the user key for that send. Error text replaces the
API token, user key, and group key with `[redacted]`.

## Config

Profiles live in `$HOME/.pushit.yml`. Pass `--config` to use another
file. `--config` requires `--profile`. `url_title` requires a `url`.
`retry` and `expire` are used only for an emergency send. There is no
profile field for a group key.

```yaml
profiles:
  alerts:
    user_key: USER_KEY
    api_token: API_TOKEN
    title: pushit
    url: https://example.com/alert
    url_title: Open
    sound: pushover
    device: phone
    priority: 0
    timeout: 15
    retry: 30
    expire: 3600
```

## Library

```python
from lupaxa.pushit import Pushit, load_profile

profile = load_profile("alerts")
client = Pushit(
    profile.api_token,
    user_key=profile.user_key,
    timeout=profile.timeout or 10.0,
)
body = client.send_message(
    "disk full",
    title="pushit",
    priority=2,
    retry=30,
    expire=3600,
    group_key="GROUP_KEY",
)
client.list_sounds()
```

`send_message` and `list_sounds` return the parsed JSON object. `load_profile` reads one named profile. The package also exports `ConfigError`, `Profile`, `default_config_path`, `DEFAULT_TIMEOUT`, `get_version`, and `__version__`.

## Reference

| Flag              | Default              | Description                                     |
| ----------------- | -------------------- | ----------------------------------------------- |
| `--user`          | profile `user_key`   | Pushover user key                               |
| `--token`         | profile `api_token`  | Application API token                           |
| `--profile`, `-p` | —                    | Profile name                                    |
| `--config`        | `~/.pushit.yml`      | Config file; requires `--profile`               |
| `--text`, `-t`    | —                    | Message, at most 1024 characters                |
| `--title`         | profile              | Title, at most 250 characters                   |
| `--url`           | profile              | Supplementary URL, at most 512 characters       |
| `--url-title`     | profile              | URL title, at most 100 characters               |
| `--priority`      | profile, else `0`    | `-2`, `-1`, `0`, or `1`                         |
| `--sound`         | profile              | Sound name                                      |
| `--device`        | profile              | Device name or comma-separated names            |
| `--attachment`    | —                    | One file path, at most 5,242,880 bytes          |
| `--emergency`     | —                    | Force priority `2`                              |
| `--retry`         | profile, else `30`   | Seconds between retries; requires `--emergency` |
| `--expire`        | profile, else `3600` | Emergency lifetime; requires `--emergency`      |
| `--group`         | —                    | Group key; replaces the user key                |
| `--sounds`        | —                    | List sorted sound names                         |
| `--timeout`, `-T` | profile, else `10`   | Positive timeout in seconds                     |
| `--version`       | —                    | Print the package version                       |

| Field         | Rule                                                                   |
| ------------- | ---------------------------------------------------------------------- |
| `user_key`    | Non-empty string; recipient unless `--user` or `--group` overrides it  |
| `api_token`   | Non-empty string; overridden by `--token`                              |
| `title`       | Non-empty string, at most 250 characters                               |
| `url`         | Non-empty string, at most 512 characters                               |
| `url_title`   | Non-empty string, at most 100 characters; requires `url`               |
| `sound`       | Non-empty string                                                       |
| `device`      | Non-empty string                                                       |
| `priority`    | Integer `-2`, `-1`, `0`, or `1`                                        |
| `timeout`     | Finite number greater than 0                                           |
| `retry`       | Integer at least 30; used only for emergency sends                     |
| `expire`      | Integer from 1 through 10,800; used only for emergency sends           |

| Code | Meaning                                                       |
| ---- | ------------------------------------------------------------- |
| 0    | Send accepted, sounds printed, help shown, or version printed |
| 1    | Validation, HTTP, or request error                            |
| 2    | Command usage or configuration error                          |

## Development

```bash
make init
make python-install-dev
make python-check
```

<a href="https://github.com/the-lupaxa-project">
    <img src="https://raw.githubusercontent.com/the-lupaxa-project/brand-assets/master/logos/components/footer-for-child-orgs.svg" alt="The Lupaxa Project Footer" width="100%" />
</a>
