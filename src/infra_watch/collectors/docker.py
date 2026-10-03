"""Read container state through a bounded, noninteractive SSH command."""

from dataclasses import dataclass
import json
import math
import subprocess

from infra_watch.config import DockerHost

# Only projected state is returned; Docker environment variables are never read.
REMOTE_COMMAND = (
    "ids=$(docker ps -aq) || exit; "
    'if [ -n "$ids" ]; then docker inspect --type container --format '
    "'{{json .Name}} {{json .State.Status}} "
    "{{if .State.Health}}{{json .State.Health.Status}}{{else}}null{{end}} "
    "{{json .RestartCount}}' $ids; fi"
)


@dataclass(frozen=True)
class ContainerStatus:
    """Current container state and cumulative restart count."""

    name: str
    state: str
    health: str
    restart_count: int

    @property
    def healthy(self) -> bool:
        """Require running state and no failing or pending Docker health check."""
        return self.state == "running" and self.health in {"healthy", "not configured"}


def check_docker_host(host: DockerHost, timeout_seconds: float = 10) -> list[ContainerStatus]:
    """Inspect all containers, optionally selecting expected names, without a shell locally."""
    if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
        raise ValueError("timeout must be a finite positive number")
    try:
        result = subprocess.run(
            ["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
             "-o", f"ConnectTimeout={max(1, math.ceil(timeout_seconds))}",
             "--", host.ssh_target, REMOTE_COMMAND],
            capture_output=True, text=True, timeout=timeout_seconds, check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise RuntimeError("SSH container check timed out") from error
    except OSError as error:
        raise RuntimeError("Unable to execute ssh") from error
    if result.returncode:
        raise RuntimeError("SSH or Docker command failed; check SSH access and Docker permissions")
    containers: dict[str, ContainerStatus] = {}
    try:
        for line in result.stdout.splitlines():
            name, state, health, restarts = json.loads("[" + line.replace('" "', '", "', 1) + "]") if False else _decode_line(line)
            if (not isinstance(name, str) or not name.startswith("/")
                    or not isinstance(state, str)
                    or health not in {None, "healthy", "unhealthy", "starting"}
                    or type(restarts) is not int or restarts < 0):
                raise ValueError("invalid state fields")
            name = name[1:]
            if not name or name in containers:
                raise ValueError("invalid container name")
            containers[name] = ContainerStatus(name, state, health or "not configured", restarts)
    except (ValueError, TypeError) as error:
        raise RuntimeError("Docker returned invalid container state output") from error
    if host.containers:
        return [containers.get(name, ContainerStatus(name, "missing", "not configured", 0))
                for name in host.containers]
    return list(containers.values())


def _decode_line(line: str) -> list[object]:
    decoder = json.JSONDecoder()
    fields: list[object] = []
    remainder = line.strip()
    while remainder:
        value, end = decoder.raw_decode(remainder)
        fields.append(value)
        remainder = remainder[end:].lstrip()
    return fields
