# Getting started

## Requirements

- Python 3.13 or later
- A Pushover user key
- A Pushover application API token
- The `requests` and `PyYAML` runtime dependencies

## Install

```bash
pip install lupaxa-pushit
```

Send a message:

```bash
pushit --user "$PUSHOVER_USER_KEY" --token "$PUSHOVER_API_TOKEN" --text "Hello"
```

## Create a profile

Profiles live in `$HOME/.pushit.yml` by default:

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

Use the profile by name:

```bash
pushit --profile alerts --text "Hello"
```

## Development

```bash
make init
make python-install-dev
make python-check
make mkdocs-serve
```
