"""Load persistent HTTP monitoring targets from TOML."""

from dataclasses import dataclass
from pathlib import Path
import tomllib

import httpx


@dataclass(frozen=True)
class HttpTarget:
    """A named application endpoint."""

    name: str
    url: str


def config_path(explicit: Path | None = None) -> Path:
    """Resolve an explicit, current-directory, or user configuration path."""
    if explicit is not None:
        return explicit.expanduser()
    local = Path("config.toml")
    if local.exists():
        return local
    return Path.home() / ".config" / "infrawatch" / "config.toml"


def load_http_targets(path: Path) -> list[HttpTarget]:
    """Read and validate all HTTP entries before any checks run."""
    try:
        with path.open("rb") as stream:
            data = tomllib.load(stream)
    except (OSError, ValueError) as error:
        raise ValueError(f"Unable to load configuration {path}: {error}") from error
    entries = data.get("http_targets", [])
    if not isinstance(entries, list):
        raise ValueError("http_targets must be an array of tables ([[http_targets]])")
    targets: list[HttpTarget] = []
    names: set[str] = set()
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict) or set(entry) != {"name", "url"}:
            raise ValueError(f"HTTP target {index} must contain only name and url")
        name, url = entry["name"], entry["url"]
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"HTTP target {index} requires a non-empty name")
        name = name.strip()
        if name in names:
            raise ValueError(f"HTTP target {index} has a duplicate name")
        if not isinstance(url, str) or not url.strip():
            raise ValueError(f"HTTP target {index} requires a non-empty URL")
        url = url.strip()
        try:
            parsed = httpx.URL(url)
        except httpx.InvalidURL as error:
            raise ValueError(f"HTTP target {index} has an invalid URL") from error
        if parsed.scheme not in {"http", "https"} or not parsed.host:
            raise ValueError(f"HTTP target {index} requires an HTTP or HTTPS URL with a host")
        names.add(name)
        targets.append(HttpTarget(name=name, url=url))
    return targets
