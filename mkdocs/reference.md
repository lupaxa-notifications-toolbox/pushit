# Reference

## Command flags

| Flag                 | Default              | Description                                           |
| -------------------- | -------------------- | ----------------------------------------------------- |
| `--user`             | profile `user_key`   | Pushover user key                                     |
| `--token`            | profile `api_token`  | Application API token                                 |
| `--profile`, `-p`    | —                    | Profile name                                          |
| `--config`           | `~/.pushit.yml`      | Config file; requires `--profile`                     |
| `--text`, `-t`       | —                    | Message, at most 1024 characters                      |
| `--title`            | profile              | Title, at most 250 characters                         |
| `--url`              | profile              | Supplementary URL, at most 512 characters             |
| `--url-title`        | profile              | URL title, at most 100 characters                     |
| `--priority`         | profile, else `0`    | `-2`, `-1`, `0`, or `1`                               |
| `--sound`            | profile              | Sound name                                            |
| `--device`           | profile              | Device name or comma-separated names                  |
| `--attachment`       | —                    | One file path, at most 5,242,880 bytes                |
| `--emergency`        | —                    | Force priority `2`                                    |
| `--retry`            | profile, else `30`   | Seconds between retries; requires `--emergency`       |
| `--expire`           | profile, else `3600` | Emergency lifetime; requires `--emergency`            |
| `--group`            | —                    | Group key; replaces the user key                      |
| `--sounds`           | —                    | List sorted sound names                               |
| `--timeout`, `-T`    | profile, else `10`   | Positive timeout in seconds                           |
| `--version`          | —                    | Print the package version                             |

## Profile fields

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

## Exit codes

| Code | Meaning                                                       |
| ---- | ------------------------------------------------------------- |
| 0    | Send accepted, sounds printed, help shown, or version printed |
| 1    | Validation, HTTP, or request error                            |
| 2    | Command usage or configuration error                          |

## Python API

The package exports these names in `__all__`:

- `Pushit`
- `DEFAULT_TIMEOUT`
- `ConfigError`
- `Profile`
- `default_config_path`
- `load_profile`
- `get_version`
- `__version__`

`Pushit.send_message` sends a notification. `Pushit.list_sounds` lists
the available sounds. Both methods return the parsed JSON object.

A successful send command prints nothing. `--sounds` is the exception:
it prints sorted sound names, one per line.
