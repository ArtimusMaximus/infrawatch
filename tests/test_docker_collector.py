"""Docker collector tests use mocked SSH, never live hosts."""

import subprocess
from types import SimpleNamespace

import pytest

from infra_watch.collectors import docker
from infra_watch.config import DockerHost


HOST = DockerHost("server", "monitor@server.test", ("app", "stopped", "missing"))


def test_collects_running_stopped_and_missing_containers(monkeypatch) -> None:
    def run(argv, **kwargs):
        assert argv[0] == "ssh"
        assert "BatchMode=yes" in argv
        assert "StrictHostKeyChecking=yes" in argv
        assert argv[-2] == HOST.ssh_target
        assert "docker ps -aq" in argv[-1]
        assert kwargs["timeout"] == 2
        return SimpleNamespace(returncode=0, stdout='"/app" "running" "healthy" 3\n"/stopped" "exited" null 0\n')
    monkeypatch.setattr(docker.subprocess, "run", run)
    results = docker.check_docker_host(HOST, 2)
    assert [r.state for r in results] == ["running", "exited", "missing"]
    assert results[0].restart_count == 3
    assert [r.healthy for r in results] == [True, False, False]


@pytest.mark.parametrize("health,expected", [(None, True), ("healthy", True), ("unhealthy", False), ("starting", False)])
def test_health_status(monkeypatch, health, expected) -> None:
    import json
    monkeypatch.setattr(docker.subprocess, "run", lambda *a, **k: SimpleNamespace(
        returncode=0, stdout=f'"/app" "running" {json.dumps(health)} 0'))
    result = docker.check_docker_host(DockerHost("server", "server.test"))[0]
    assert result.healthy == expected


@pytest.mark.parametrize("output", ['garbage', '"/app" "running" null', '"/app" "running" null -1', '"/app" "running" null true'])
def test_invalid_output(monkeypatch, output) -> None:
    monkeypatch.setattr(docker.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=0, stdout=output))
    with pytest.raises(RuntimeError, match="invalid container"):
        docker.check_docker_host(HOST)


@pytest.mark.parametrize("error,message", [(subprocess.TimeoutExpired("ssh", 1), "timed out"), (FileNotFoundError(), "execute ssh")])
def test_ssh_exceptions(monkeypatch, error, message) -> None:
    def run(*a, **k):
        raise error
    monkeypatch.setattr(docker.subprocess, "run", run)
    with pytest.raises(RuntimeError, match=message):
        docker.check_docker_host(HOST)


def test_remote_failure(monkeypatch) -> None:
    monkeypatch.setattr(docker.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=255))
    with pytest.raises(RuntimeError, match="permissions"):
        docker.check_docker_host(HOST)


@pytest.mark.parametrize("timeout", [0, -1, float("nan"), float("inf")])
def test_invalid_timeout(timeout) -> None:
    with pytest.raises(ValueError):
        docker.check_docker_host(HOST, timeout)
