<p align="center">
  <a href="https://github.com/lupaxa-notifications-toolbox">
    <img src="https://raw.githubusercontent.com/the-lupaxa-project/brand-assets/master/logos/organisations/notifications-toolbox/readme-logo.png" alt="Notifications Toolbox" />
  </a>
</p>

<h1 align="center">pushit</h1>

Send Pushover notifications.

<p align="center">
  <a href="https://pushit.thelupaxaproject.org/">Documentation</a>
  ·
  <a href="https://github.com/lupaxa-notifications-toolbox/pushit">GitHub</a>
</p>

## Install

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

`--text` is the message. `--emergency` and `--group` may be combined
with it. `--sounds` cannot be combined with a send. The `$PUSHOVER_*`
names are shell variables expanded before pushit runs; pushit does not
read environment variables.

## Config

Profiles live in `$HOME/.pushit.yml`. Pass `--config` to use another
file; `--config` requires `--profile`.

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

## Development

```bash
make init
make python-install-dev
make python-check
make mkdocs-serve
```

<a href="https://github.com/the-lupaxa-project">
    <img src="https://raw.githubusercontent.com/the-lupaxa-project/brand-assets/master/logos/components/footer-for-child-orgs.svg" alt="The Lupaxa Project Footer" width="100%" />
</a>
