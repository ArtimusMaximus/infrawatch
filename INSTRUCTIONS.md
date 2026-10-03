# Getting back into InfraWatch

## Every time you return

Open a terminal and run:

```bash
cd /home/amiv/projects3/python_infraWatch
source .venv/bin/activate
infrawatch status
```

Yes, this project uses a Python virtual environment (`.venv`). Activate it in
each new terminal. InfraWatch currently runs as a CLI; each command finishes
after reporting its results.

## First-time setup (or if `.venv` is missing)

Use Python 3.12 or newer:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

If `infrawatch` is missing after activation, rerun the install command above.
The editable install picks up source changes without reinstalling; reinstall
when dependencies or package configuration change.

## Try the local health-check demo

In terminal one, from the project root:

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
```

`/health` returns healthy (HTTP 200); `/unhealthy` intentionally returns
unhealthy (HTTP 503). Stop the server with `Ctrl+C`.

To check both using a temporary target list:

```bash
export INFRAWATCH_TARGETS="http://127.0.0.1:8000/health http://127.0.0.1:8000/unhealthy"
infrawatch check all --timeout 2
echo $?
```

The variable lasts for the current terminal session. `.env` files are not
loaded automatically. Exit codes: `0` = all healthy, `1` = any unhealthy,
`2` = invalid input. Checks run sequentially with a timeout per request.

## Persistent targets

Your root `config.toml` stores targets independently of `.venv`. Edit or add
entries, then run:

```bash
unset INFRAWATCH_TARGETS
infrawatch check all
```

Each target uses this structure (replace the example URL):

```toml
[[http_targets]]
name = "example-app"
url = "https://app.example.com/health"
```

Lookup order: `--config PATH`, then `./config.toml`, then
`~/.config/infrawatch/config.toml`. Every `check all` rereads the file.
`INFRAWATCH_TARGETS`, if set, overrides the file, including when empty.
For initial setup, copy `examples/config.example.toml` to `config.toml`.
Personal config files are ignored by Git. Docker host entries are not used yet.

## Check the project

```bash
python -m pytest
```

The unit tests mock system readings and HTTP requests; no running demo server
or network connection is needed. Leave the environment with `deactivate`.

## Where we left off

- Current package version: **0.2.0**, the local monitoring CLI milestone.
- `infrawatch status`: hostname, OS, uptime, CPU, memory, disk, and IP address.
- `infrawatch check URL [URL ...]`: HTTP health, status code, response time,
  timestamp, failure handling, and a summary for multiple targets.
- `infrawatch check all`: persistent TOML targets, with an optional
  `INFRAWATCH_TARGETS` override.
- A local demo server and pytest coverage for collectors and CLI behavior.
- FastAPI, PostgreSQL, Prometheus, Grafana, Docker Compose, scheduling,
  alerting, and remediation are future phases.

Application code lives in `src/infra_watch/`, tests in `tests/`, and the demo
in `examples/`. See [README.md](README.md) for more detail. Next milestone: inspect container state over SSH on the configured Docker
host, after reviewing persistent configuration.


## Git workflow

Keep each feature on its own branch. Review and validate before merging:

```bash
git switch master
git switch -c feature/short-description
# Make a focused change, inspect the diff, and run tests.
git diff
python -m pytest
git add <specific-files>
git commit -m "Add focused feature"
```

For this change, the branch is `feature/persistent-target-config`. Once you
approve the change and finish your manual check:

```bash
git switch master
git merge --no-ff feature/persistent-target-config
```

The merge commit preserves the feature's branch history. On a shared remote,
push the branch and open a pull request for review, then merge through the
team's pull-request workflow.
