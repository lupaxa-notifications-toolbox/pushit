<!-- markdownlint-disable -->
<p align="center">
  <a href="https://github.com/lupaxa-notifications-toolbox">
    <img src="https://raw.githubusercontent.com/the-lupaxa-project/brand-assets/master/logos/organisations/notifications-toolbox/readme-logo.png" alt="Project Logo" width="256"/><br/>
  </a>
</p>
<h3 align="center">
  The Lupaxa Notifications Toolbox<br />
  Part of The Lupaxa Project
</h3>

<br />

# lupaxa-pushit

Send Pushover notifications.

## Features

- Send a message with an optional title and supplementary URL
- Set priority, sound, and one or more target devices
- Upload one attachment
- Configure emergency retry and expiry values
- Deliver to a Pushover group
- List available Pushover sounds
- Keep named profiles in `$HOME/.pushit.yml`
- Use the `Pushit` library class or the `pushit` command

## Installation

### From PyPI

```bash
pip install lupaxa-pushit
```

### From source (development mode)

```bash
pip install -e ".[dev]"
```

Requires Python 3.13+. Runtime dependencies: `requests` and `PyYAML`.

## Library quick start

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

## CLI quick start

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

<a href="https://github.com/the-lupaxa-project">
    <img src="https://raw.githubusercontent.com/the-lupaxa-project/brand-assets/master/logos/components/footer-for-child-orgs.svg" alt="The Lupaxa Project Footer" width="100%" />
</a>
