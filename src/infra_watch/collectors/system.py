"""Collect metrics from the local operating system."""

import logging
import platform
import socket
import time

import psutil

from infra_watch.models import SystemMetrics

LOGGER = logging.getLogger(__name__)


def _primary_ip_address() -> str:
    """Return the first non-loopback IPv4 address, if one is available."""
    try:
        interfaces = psutil.net_if_addrs()
    except OSError as error:
        LOGGER.warning("Unable to inspect network interfaces: %s", error)
        return "unavailable"

    for addresses in interfaces.values():
        for address in addresses:
            if address.family == socket.AF_INET and not address.address.startswith("127."):
                return str(address.address)
    return "unavailable"


def collect_system_metrics() -> SystemMetrics:
    """Collect a single snapshot of metrics for the local machine."""
    LOGGER.debug("Collecting local system metrics")
    uptime_seconds = max(0.0, time.time() - psutil.boot_time())

    metrics = SystemMetrics(
        hostname=socket.gethostname(),
        operating_system=f"{platform.system()} {platform.release()}",
        uptime_seconds=uptime_seconds,
        cpu_percent=psutil.cpu_percent(interval=0.1),
        memory_percent=psutil.virtual_memory().percent,
        disk_percent=psutil.disk_usage("/").percent,
        ip_address=_primary_ip_address(),
    )
    LOGGER.info("Collected local system metrics for host %s", metrics.hostname)
    return metrics

