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


@dataclass(frozen=True)
class DockerHost:
    """SSH host and optional expected container names."""

    name: str
    ssh_target: str
    containers: tuple[str, ...] = ()


def load_docker_hosts(path: Path) -> list[DockerHost]:
    """Validate Docker inventory without contacting hosts."""
    import re

    try:
        with path.open("rb") as stream:
            entries = tomllib.load(stream).get("docker_hosts", [])
    except (OSError, ValueError) as error:
        raise ValueError(f"Unable to load configuration {path}") from error
    if not isinstance(entries, list):
        raise ValueError("docker_hosts must be an array of tables")
    hosts: list[DockerHost] = []
    names: set[str] = set()
    for index, entry in enumerate(entries, 1):
        if not isinstance(entry, dict) or set(entry) - {"name", "ssh_target", "containers"}:
            raise ValueError(f"Docker host {index} has invalid fields")
        name = entry.get("name")
        target = entry.get("ssh_target")
        containers = entry.get("containers", [])
        if not isinstance(name, str) or not name.strip() or name.strip() in names:
            raise ValueError(f"Docker host {index} requires a unique non-empty name")
        if not isinstance(target, str) or not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.@:-]*", target):
            raise ValueError(f"Docker host {index} requires an SSH alias or user@host")
        if (not isinstance(containers, list)
                or any(not isinstance(c, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", c) for c in containers)
                or len(set(containers)) != len(containers)):
            raise ValueError(f"Docker host {index} has invalid or duplicate container names")
        names.add(name.strip())
        hosts.append(DockerHost(name.strip(), target, tuple(containers)))
    return hosts
