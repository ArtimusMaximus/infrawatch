"""Tests for the InfraWatch CLI."""

from datetime import datetime, timezone

import httpx
import pytest

from infra_watch import cli
from infra_watch.collectors.http import check_http_health
from infra_watch.models import HealthCheckResult, SystemMetrics


def test_status_command_prints_metrics(monkeypatch, capsys) -> None:
    metrics = SystemMetrics(
        hostname="test-host",
        operating_system="TestOS 1.2.3",
        uptime_seconds=90_061,
        cpu_percent=12.5,
        memory_percent=45.5,
        disk_percent=67.5,
        ip_address="192.0.2.10",
    )
    monkeypatch.setattr(cli, "collect_system_metrics", lambda: metrics)

    exit_code = cli.main(["status"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Hostname: test-host" in output
    assert "Uptime: 1d 1h 1m 1s" in output
    assert "CPU utilization: 12.5%" in output
    assert "IP address: 192.0.2.10" in output


def test_status_command_returns_failure_when_collection_fails(
    monkeypatch, caplog
) -> None:
    def fail_collection() -> SystemMetrics:
        raise RuntimeError("collection failed")

    monkeypatch.setattr(cli, "collect_system_metrics", fail_collection)

    assert cli.main(["status"]) == 1
    assert "Unable to collect local system metrics" in caplog.text


def test_check_command_returns_success_for_healthy_endpoint(
    monkeypatch, capsys
) -> None:
    result = HealthCheckResult(
        target_url="http://localhost:8000/health",
        healthy=True,
        checked_at=datetime(2026, 9, 5, 12, 0, tzinfo=timezone.utc),
        response_time_ms=12.34,
        status_code=200,
    )
    monkeypatch.setattr(cli, "check_http_health", lambda url, timeout: result)

    exit_code = cli.main(["check", result.target_url])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Status: healthy" in output
    assert "HTTP status: 200" in output
    assert "Response time: 12.3 ms" in output


def test_check_command_returns_failure_for_unhealthy_endpoint(
    monkeypatch, capsys
) -> None:
    result = HealthCheckResult(
        target_url="http://localhost:8000/unhealthy",
        healthy=False,
        checked_at=datetime(2026, 9, 5, 12, 0, tzinfo=timezone.utc),
        response_time_ms=8.0,
        status_code=503,
    )
    monkeypatch.setattr(cli, "check_http_health", lambda url, timeout: result)

    exit_code = cli.main(["check", result.target_url, "--timeout", "1"])

    assert exit_code == 1
    assert "Status: unhealthy" in capsys.readouterr().out


def test_check_command_rejects_non_positive_timeout(monkeypatch) -> None:
    def reject_timeout(url: str, timeout: float) -> HealthCheckResult:
        raise ValueError("timeout_seconds must be greater than zero")

    monkeypatch.setattr(cli, "check_http_health", reject_timeout)

    assert cli.main(["check", "http://localhost", "--timeout", "0"]) == 2


def test_check_command_returns_invalid_input_exit_code(monkeypatch) -> None:
    def reject_url(url: str, timeout: float) -> HealthCheckResult:
        raise ValueError("target URL must include an HTTP or HTTPS scheme and host")

    monkeypatch.setattr(cli, "check_http_health", reject_url)

    assert cli.main(["check", "localhost/health"]) == 2


@pytest.mark.parametrize(
    ("first_outcome", "expected_exit", "expected_summary"),
    [
        ("healthy", 0, "2 healthy, 0 unhealthy, 0 invalid"),
        ("unhealthy", 1, "1 healthy, 1 unhealthy, 0 invalid"),
        ("connection", 1, "1 healthy, 1 unhealthy, 0 invalid"),
        ("timeout", 1, "1 healthy, 1 unhealthy, 0 invalid"),
        ("invalid", 2, "1 healthy, 0 unhealthy, 1 invalid"),
    ],
)
def test_check_command_checks_remaining_targets(
    monkeypatch, capsys, first_outcome: str, expected_exit: int,
    expected_summary: str,
) -> None:
    requested_urls: list[str] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requested_urls.append(str(request.url))
        assert request.extensions["timeout"]["read"] == 2.0
        if request.url.host == "first.test":
            if first_outcome == "connection":
                raise httpx.ConnectError("connection refused", request=request)
            if first_outcome == "timeout":
                raise httpx.ReadTimeout("request timed out", request=request)
            if first_outcome == "unhealthy":
                return httpx.Response(503, request=request)
        return httpx.Response(200, request=request)

    first_url = (
        "invalid/health" if first_outcome == "invalid"
        else "https://first.test/health"
    )
    second_url = "https://second.test/health"
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        def check(url: str, timeout: float) -> HealthCheckResult:
            return check_http_health(url, timeout, client=client)

        monkeypatch.setattr(cli, "check_http_health", check)
        exit_code = cli.main(["check", first_url, second_url, "--timeout", "2"])

    output = capsys.readouterr().out
    assert exit_code == expected_exit
    assert f"Target: {first_url}" in output
    assert f"Target: {second_url}" in output
    assert f"Summary: {expected_summary} (2 total)" in output
    assert requested_urls == (
        [second_url] if first_outcome == "invalid" else [first_url, second_url]
    )


def test_check_command_invalid_input_takes_precedence_over_unhealthy(
    monkeypatch, capsys,
) -> None:
    def check(url: str, timeout: float) -> HealthCheckResult:
        if url == "invalid":
            raise ValueError("invalid URL")
        return HealthCheckResult(
            target_url=url, healthy=False,
            checked_at=datetime.now(timezone.utc), response_time_ms=1,
            status_code=503,
        )

    monkeypatch.setattr(cli, "check_http_health", check)

    assert cli.main(["check", "invalid", "https://service.test/health"]) == 2
    assert "0 healthy, 1 unhealthy, 1 invalid" in capsys.readouterr().out


def test_check_all_uses_configured_targets(monkeypatch, capsys) -> None:
    monkeypatch.setenv(
        "INFRAWATCH_TARGETS",
        " https://first.test/health\n https://second.test/health ",
    )
    checked: list[tuple[str, float]] = []

    def check(url: str, timeout: float) -> HealthCheckResult:
        checked.append((url, timeout))
        return HealthCheckResult(
            target_url=url, healthy=url == "https://first.test/health",
            checked_at=datetime.now(timezone.utc), response_time_ms=1,
        )

    monkeypatch.setattr(cli, "check_http_health", check)
    assert cli.main(["check", "all", "--timeout", "2"]) == 1
    assert checked == [
        ("https://first.test/health", 2.0),
        ("https://second.test/health", 2.0),
    ]
    assert "1 healthy, 1 unhealthy, 0 invalid (2 total)" in capsys.readouterr().out


@pytest.mark.parametrize("targets", [None, "", " \n\t "])
def test_check_all_requires_targets(monkeypatch, caplog, targets: str | None) -> None:
    if targets is None:
        monkeypatch.delenv("INFRAWATCH_TARGETS", raising=False)
    else:
        monkeypatch.setenv("INFRAWATCH_TARGETS", targets)

    def unexpected_check(url: str, timeout: float) -> HealthCheckResult:
        pytest.fail("No request should be made without targets")

    monkeypatch.setattr(cli, "check_http_health", unexpected_check)
    assert cli.main(["check", "all"]) == 2
    assert "Set INFRAWATCH_TARGETS" in caplog.text


def test_check_all_rejects_additional_urls(monkeypatch, caplog) -> None:
    def unexpected_check(url: str, timeout: float) -> HealthCheckResult:
        pytest.fail("Ambiguous input should not make requests")

    monkeypatch.setattr(cli, "check_http_health", unexpected_check)
    assert cli.main(["check", "all", "https://service.test/health"]) == 2
    assert "Use 'all' on its own" in caplog.text
