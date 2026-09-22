# Examples

Send with explicit credentials:

```bash
pushit --user "$PUSHOVER_USER_KEY" --token "$PUSHOVER_API_TOKEN" --text "Hello"
```

Send with the default profile file:

```bash
pushit --profile alerts --text "Hello"
```

Use another profile file:

```bash
pushit -p alerts --config "$HOME/work/pushit.yml" --text "Disk full"
```

Send an emergency group notification:

```bash
pushit --profile alerts --text "down" --emergency --group "$PUSHOVER_GROUP_KEY"
```

Add a title and supplementary URL:

```bash
pushit --profile alerts --text "see" --title pushit --url https://example.com --url-title Open
```

Send an attachment with sound and device selection:

```bash
pushit --profile alerts --text "see" --attachment report.png --sound pushover --device phone
```

List available sounds:

```bash
pushit --token "$PUSHOVER_API_TOKEN" --sounds
```

Print the package version:

```bash
python -m lupaxa.pushit --version
```
