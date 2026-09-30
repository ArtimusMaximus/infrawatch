"""Domain model for application health checks."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class HealthCheckResult:
    """The outcome of one HTTP health check."""

    target_url: str
    healthy: bool
    checked_at: datetime
    response_time_ms: float
    status_code: int | None = None
    error: str | None = None

