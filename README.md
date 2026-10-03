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
and an HTTP/HTTPS `url`. Docker entries configure the SSH container checks described below.
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
Docker Compose deployment, cloud metrics, alerting, and automated remediation.
Read-only Docker container checks over SSH are supported.


## Container status over SSH

An HTTP response checks app availability. Docker inspection checks the underlying
container independently: running state, Docker health status, and cumulative
restart count. Configure hosts in the same TOML file:

```toml
[[docker_hosts]]
name = "example-server"
ssh_target = "monitor@example-server"
containers = ["example-app"]
```

`containers` lists expected names; a missing container is reported as `missing`.
Omit the list or set it to `[]` to inspect all containers, including stopped ones.
No Docker daemon API exposure or Python SSH dependency is required. The remote
SSH account must be able to run Docker without a password prompt. Establish and
verify the host key with your normal interactive SSH login first, and configure
SSH keys or an agent. InfraWatch uses `BatchMode=yes` and strict host-key checking;
it does not prompt for passwords or automatically trust unknown hosts.

```bash
infrawatch containers
infrawatch containers example-server --timeout 10
infrawatch containers --config /path/to/config.toml
```

The timeout bounds the entire SSH subprocess per host. Host checks are sequential;
a failed host does not stop the others. Exit codes: `0` = all inspected containers
running with healthy or unconfigured health checks; `1` = a host error or a
container missing, stopped, restarting, unhealthy, or still starting; `2` =
invalid configuration, unknown host, or invalid timeout. An empty server reports
no containers and exits successfully unless specific expected names were listed.
Restart counts are informational; a count above zero alone does not fail a check.
A container without `HEALTHCHECK` is labeled `not configured`, not `healthy`.

To validate manually, compare the output with `docker ps -a` and `docker inspect`
on the remote server. These commands only inspect state; they do not change
container configuration or restart services. On SSH errors, verify connectivity
and permissions with `ssh USER@HOST 'docker ps -a'`.

## Manage saved HTTP targets

```bash
infrawatch targets list
infrawatch targets add example-app https://app.example.com/health
infrawatch targets remove example-app
# All three actions accept --config PATH after the action.
```

These commands manage the file, regardless of `INFRAWATCH_TARGETS`. Unset that
variable to make `check all` use file changes. Names must be unique; duplicate
adds and removal of unknown names return `2`. Add creates a missing file and
parent directory. New files use owner-only permissions. Existing permissions
are preserved. Edits validate the candidate file and replace it atomically,
using an exclusive `.lock` file and detecting external changes before replacement.
Docker entries and unrelated configuration are preserved. Removal supports
standard `[[http_targets]]` tables; alternate TOML layouts must be edited manually.
Comments inside a removed target are removed along with it. If a killed process
leaves a `.lock` file, confirm no editor command is running before deleting that
lock. Symlink config files are rejected for editing.

Manual check without changing your inventory:

```bash
infrawatch targets add demo http://127.0.0.1:8000/health --config /tmp/infrawatch-demo.toml
infrawatch targets list --config /tmp/infrawatch-demo.toml
infrawatch targets remove demo --config /tmp/infrawatch-demo.toml
```
