# Repository Guidelines

## Purpose & Direction

InfraWatch is an educational, production-style Python platform for infrastructure monitoring and automation. It should demonstrate practical systems engineering skills without implementing the entire platform at once.

The planned architecture uses Python 3.12+, FastAPI for the control-plane API, PostgreSQL for application state, Prometheus for time-series metrics, Grafana for visualization, Docker Compose for local infrastructure, and pytest for testing. Treat these as phased goals: introduce each technology only when the current milestone requires it.

## Project Structure & Module Organization

Keep metadata and documentation at the repository root. Place application code in `src/infra_watch/` and tests in `tests/`, mirroring source modules where practical. Use `tests/fixtures/` for sanitized test data, `examples/` for sample configuration, and `docs/` for design decisions. Centralize dependencies and tool settings in `pyproject.toml`.

## Development Workflow

Do not implement large features before explaining the proposed design and tradeoffs. Prefer small, testable components and focused changes; do not modify unrelated files. Before introducing a dependency, explain what problem it solves and why the standard library is insufficient.

For each infrastructure concept:

1. Explain the concept.
2. Explain why the design fits InfraWatch.
3. Implement it incrementally.
4. Explain how to test it manually.

When tooling is available, the expected workflow is:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m pytest
```

## Coding Style & Naming Conventions

Use four-space indentation, required type hints, and concise docstrings for public or non-obvious behavior. Use `snake_case` for modules, functions, and variables; `PascalCase` for classes; and `UPPER_SNAKE_CASE` for constants. Prefer structured logging over `print`. Load configuration from environment variables and keep integration boundaries mockable. Configure formatting, linting, and type checking centrally; Ruff is preferred when tooling is established.

## Testing Guidelines

Use pytest and add tests with new functionality. Name files `test_<module>.py` and tests `test_<behavior>`. Cover success, failure, and timeout paths. Unit tests must not require live networks, hosts, containers, or credentials. Add a regression test for every bug fix and run relevant tests after modifying code.

## Commits, Reviews & Security

Use short, imperative commit subjects such as `Add HTTP health check`. Keep commits focused. Pull requests should explain the problem, design, validation performed, and relevant issue; include operational evidence when useful. Never commit secrets, private keys, inventories, or `.env` files. Provide sanitized templates such as `.env.example` and redact sensitive values from logs and fixtures.
