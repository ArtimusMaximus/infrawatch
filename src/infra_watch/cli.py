"""Command-line interface for InfraWatch."""

import argparse
import logging
import os
from collections.abc import Sequence

from infra_watch.collectors import check_http_health, collect_system_metrics
from infra_watch.models import HealthCheckResult, SystemMetrics

LOGGER = logging.getLogger(__name__)


def _format_uptime(seconds: float) -> str:
    total_seconds = int(seconds)
    days, remainder = divmod(total_seconds, 86_400)
    hours, remainder = divmod(remainder, 3_600)
    minutes, remaining_seconds = divmod(remainder, 60)
    return f"{days}d {hours}h {minutes}m {remaining_seconds}s"


def _render_status(metrics: SystemMetrics) -> str:
    return "\n".join(
        (
            f"Hostname: {metrics.hostname}",
            f"Operating system: {metrics.operating_system}",
            f"Uptime: {_format_uptime(metrics.uptime_seconds)}",
            f"CPU utilization: {metrics.cpu_percent:.1f}%",
            f"Memory utilization: {metrics.memory_percent:.1f}%",
            f"Disk utilization: {metrics.disk_percent:.1f}%",
            f"IP address: {metrics.ip_address}",
        )
    )


def _render_health_check(result: HealthCheckResult) -> str:
    status_code = str(result.status_code) if result.status_code is not None else "unavailable"
    lines = [
        f"Target: {result.target_url}",
        f"Status: {'healthy' if result.healthy else 'unhealthy'}",
        f"HTTP status: {status_code}",
        f"Response time: {result.response_time_ms:.1f} ms",
        f"Checked at: {result.checked_at.isoformat()}",
    ]
    if result.error is not None:
        lines.append(f"Error: {result.error}")
    return "\n".join(lines)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="infrawatch", description="Inspect local infrastructure health."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("status", help="Report metrics for the local machine.")
    check_parser = subparsers.add_parser(
        "check", help="Check the health of one or more HTTP endpoints."
    )
    check_parser.add_argument(
        "urls", nargs="+",
        help="HTTP or HTTPS URLs, or 'all' to check INFRAWATCH_TARGETS."
    )
    check_parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        metavar="SECONDS",
        help="Request timeout in seconds (default: 5).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the InfraWatch command-line interface."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = _build_parser().parse_args(argv)

    if args.command == "status":
        try:
            print(_render_status(collect_system_metrics()))
        except Exception:
            LOGGER.exception("Unable to collect local system metrics")
            return 1
    elif args.command == "check":
        urls = args.urls
        if "all" in urls:
            if urls != ["all"]:
                LOGGER.error("Use 'all' on its own, without additional URLs")
                return 2
            urls = os.environ.get("INFRAWATCH_TARGETS", "").split()
            if not urls:
                LOGGER.error(
                    "No targets configured. Set INFRAWATCH_TARGETS to "
                    "a space-separated list of HTTP or HTTPS URLs"
                )
                return 2
        healthy_count = 0
        unhealthy_count = 0
        invalid_count = 0
        for index, url in enumerate(urls):
            if index:
                print()
            try:
                result = check_http_health(url, args.timeout)
            except ValueError as error:
                LOGGER.error("Invalid health check: %s", error)
                print(f"Target: {url}\nStatus: invalid\nError: {error}")
                invalid_count += 1
                continue
            print(_render_health_check(result))
            if result.healthy:
                healthy_count += 1
            else:
                unhealthy_count += 1
        if len(urls) > 1 or args.urls == ["all"]:
            print(
                f"\nSummary: {healthy_count} healthy, "
                f"{unhealthy_count} unhealthy, {invalid_count} invalid "
                f"({len(urls)} total)"
            )
        if invalid_count:
            return 2
        return 1 if unhealthy_count else 0
    return 0
