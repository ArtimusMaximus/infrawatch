"""Domain model for local host observations."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SystemMetrics:
    """A point-in-time snapshot of local system health."""

    hostname: str
    operating_system: str
    uptime_seconds: float
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    ip_address: str

