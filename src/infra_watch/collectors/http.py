"""Perform HTTP application health checks."""

import logging
import time
from datetime import datetime, timezone

import httpx

from infra_watch.models import HealthCheckResult

LOGGER = logging.getLogger(__name__)


def check_http_health(
    target_url: str,
    timeout_seconds: float = 5.0,
    *,
    client: httpx.Client | None = None,
) -> HealthCheckResult:
    """Check an HTTP endpoint, treating any 2xx response as healthy."""
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be greater than zero")
    try:
        parsed_url = httpx.URL(target_url)
    except httpx.InvalidURL as error:
        raise ValueError(f"invalid target URL: {error}") from error
    if parsed_url.scheme not in {"http", "https"} or parsed_url.host is None:
        raise ValueError("target URL must include an HTTP or HTTPS scheme and host")

    checked_at = datetime.now(timezone.utc)
    started_at = time.perf_counter()
    LOGGER.info("Checking HTTP health endpoint %s", target_url)

    try:
        if client is None:
            with httpx.Client(timeout=timeout_seconds) as managed_client:
                response = managed_client.get(target_url)
        else:
            response = client.get(target_url, timeout=timeout_seconds)
    except httpx.RequestError as error:
        response_time_ms = (time.perf_counter() - started_at) * 1_000
        LOGGER.warning("HTTP health check failed for %s: %s", target_url, error)
        return HealthCheckResult(
            target_url=target_url,
            healthy=False,
            checked_at=checked_at,
            response_time_ms=response_time_ms,
            error=str(error),
        )

    response_time_ms = (time.perf_counter() - started_at) * 1_000
    healthy = 200 <= response.status_code < 300
    LOGGER.info(
        "HTTP health check completed for %s with status %s",
        target_url,
        response.status_code,
    )
    return HealthCheckResult(
        target_url=target_url,
        healthy=healthy,
        checked_at=checked_at,
        response_time_ms=response_time_ms,
        status_code=response.status_code,
    )
