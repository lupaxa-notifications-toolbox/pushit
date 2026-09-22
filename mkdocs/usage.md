# Usage

## Command modes

`--text` is required for a send. `--emergency` and `--group` may be
combined. `--priority` cannot be combined with `--emergency`, and
`--retry` and `--expire` require `--emergency`.

`--sounds` lists sound names and cannot be combined with a send. It may
be used with `--token` and `--user`.

## Command flags

- `--user`: Pushover user key
- `--token`: application API token
- `--profile`, `-p`: profile name
- `--config`: config path; requires `--profile`
- `--text`, `-t`: message text, at most 1024 characters
- `--title`: title, at most 250 characters
- `--url`: supplementary URL, at most 512 characters
- `--url-title`: supplementary URL title, at most 100 characters
- `--priority`: `-2`, `-1`, `0`, or `1`
- `--sound`: sound name
- `--device`: device name or comma-separated names
- `--attachment`: one file, at most 5,242,880 bytes
- `--emergency`: force priority `2`
- `--retry`: seconds between emergency retries, at least 30
- `--expire`: emergency lifetime from 1 through 10,800 seconds
- `--group`: group key, replacing the user key for this send
- `--sounds`: list available sound names
- `--timeout`, `-T`: positive request timeout in seconds
- `--version`: print the package version

CLI values override profile values. Error text replaces the API token,
user key, and group key with `[redacted]`.

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
