# Pushit

Pushit sends Pushover notifications from a command or from Python. It
supports named YAML profiles, emergency delivery, groups, attachments,
sounds, priorities, URLs, and device selection.

## Install

```bash
pip install lupaxa-pushit
```

Send a first message with explicit credentials:

```bash
pushit --user "$PUSHOVER_USER_KEY" --token "$PUSHOVER_API_TOKEN" --text "Hello"
```

A successful send prints nothing. The Python library returns the parsed
JSON response body.

## Documentation

- [Getting started](getting-started.md)
- [Usage](usage.md)
- [Reference](reference.md)
- [Examples](examples.md)
