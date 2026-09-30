"""Tests for HTTP application health checks."""

import httpx
import pytest

from infra_watch.collectors.http import check_http_health


@pytest.mark.parametrize(
    ("status_code", "expected_health"),
    [(200, True), (204, True), (301, False), (503, False)],
)
def test_check_http_health_classifies_response(
    status_code: int, expected_health: bool
) -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(status_code, request=request)
    )

    with httpx.Client(transport=transport) as client:
        result = check_http_health("https://service.test/health", client=client)

    assert result.healthy is expected_health
    assert result.status_code == status_code
    assert result.error is None
    assert result.response_time_ms >= 0
    assert result.checked_at.tzinfo is not None


def test_check_http_health_records_connection_failure() -> None:
    def fail_connection(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    transport = httpx.MockTransport(fail_connection)

    with httpx.Client(transport=transport) as client:
        result = check_http_health("https://service.test/health", client=client)

    assert result.healthy is False
    assert result.status_code is None
    assert result.error == "connection refused"


def test_check_http_health_rejects_non_positive_timeout() -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        check_http_health("https://service.test/health", timeout_seconds=0)


def test_check_http_health_rejects_url_without_http_scheme() -> None:
    with pytest.raises(ValueError, match="HTTP or HTTPS scheme and host"):
        check_http_health("service.test/health")
