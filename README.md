# InfraWatch

InfraWatch is a production-style infrastructure monitoring project built for
learning practical systems engineering. The current CLI milestone
reports local host metrics and checks HTTP application health endpoints.

## Requirements

- Python 3.12 or newer
- A Linux, macOS, or Windows host supported by `psutil`

## Installation

Create an isolated environment and install the application with development
tools:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
```

## Usage

Report metrics for the machine running InfraWatch:

```bash
infrawatch status
```

Check an application health endpoint:

```bash
infrawatch check https://example.com/health
infrawatch check https://example.com/health --timeout 2
```

Check several services in one command (replace these example URLs with your
own reachable service endpoints):

```bash
infrawatch check https://app.example.com/health https://api.example.com/health --timeout 2
```

Checks run sequentially, using the timeout for each request. Each endpoint gets
its own result, followed by a summary. An unhealthy, unreachable, timed-out, or
invalid target does not prevent checks of the remaining targets. The command
exits with `0` when all targets are healthy, `1` when any are unhealthy, or `2`
when any input is invalid (taking precedence over unhealthy results).

To persist targets across terminal sessions and virtual-environment recreation,
copy `examples/config.example.toml` to `config.toml` in the project root, then
edit its named `[[http_targets]]` entries. Personal `config.toml` files are
ignored by Git. Alternatively, store the file at
`~/.config/infrawatch/config.toml` for use from any working directory.

```bash
cp examples/config.example.toml config.toml
# Edit config.toml with your actual application URLs.
infrawatch check all
infrawatch check all --config /path/to/config.toml --timeout 2
```

File lookup uses `--config PATH`, then `./config.toml`, then the user config.
The file is read afresh for each `check all`; no restart is required. Invalid
TOML, unreadable files, invalid HTTP entries, and duplicate names return exit
code `2` before requests start. Each HTTP entry requires a non-empty `name`
and an HTTP/HTTPS `url`. Docker entries are reserved and not used yet.
Explicit URL checks and `status` do not require a configuration file.

An explicitly set `INFRAWATCH_TARGETS` overrides the file for `check all`, even
when empty. Use `unset INFRAWATCH_TARGETS` to return to file-based targets.

For a temporary space-separated target list in your terminal:

```bash
export INFRAWATCH_TARGETS="http://127.0.0.1:8000/health http://127.0.0.1:8000/unhealthy"
infrawatch check all
infrawatch check all --timeout 2
```

Replace the demo URLs with your services. The variable lasts for the current
terminal session; to keep it for future Bash terminals, add the `export` line
to your personal `~/.bashrc` and load it with `source ~/.bashrc`. Configuration
is read from the environment; `.env` files are not loaded automatically.
`all` must be used on its own, without additional URLs. An unset or empty list
exits with code `2` and explains how to configure targets. Explicit URL checks
continue to work independently of this saved list.

The command name is registered in `pyproject.toml`:

```toml
[project.scripts]
infrawatch = "infra_watch.cli:main"
```

Installing the package creates an `infrawatch` launcher in `.venv/bin/` that
calls `main()` in `src/infra_watch/cli.py`. Activating the environment puts that
directory on your terminal's `PATH`. The CLI uses `argparse` to interpret
subcommands such as `status` and `check`.

Any HTTP `2xx` response is healthy. Other responses and connection failures are
unhealthy. A healthy check exits with code `0`; an unhealthy check exits with
code `1`; invalid input exits with code `2`. Inspect the last exit code with
`echo $?`.

The CPU measurement samples utilization for a short interval. Disk utilization
currently refers to the filesystem containing `/`. The reported address is the
first non-loopback IPv4 address visible to the operating system.

## Tests

Run the isolated unit tests with:

```bash
python -m pytest
```

Tests mock operating-system readings and do not require network connectivity or
privileged access.

## Local Demo

In terminal one, activate the environment and start the demo service:

```bash
source .venv/bin/activate
python examples/demo_health_server.py
```

In terminal two:

```bash
cd /home/amiv/projects3/python_infraWatch
source .venv/bin/activate
infrawatch check http://127.0.0.1:8000/health
infrawatch check http://127.0.0.1:8000/unhealthy
infrawatch check http://127.0.0.1:8000/health http://127.0.0.1:8000/unhealthy --timeout 2
echo $?
```

Stop the demo server with `Ctrl+C`.

## Current Scope

The current milestone intentionally excludes scheduling, APIs, databases, Prometheus, Grafana,
Docker, cloud monitoring, remote nodes, alerting, and automated remediation.
