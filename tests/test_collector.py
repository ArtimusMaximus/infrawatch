"""Tests for local metric collection."""

import socket
from types import SimpleNamespace

from infra_watch.collectors import system


def test_collect_system_metrics(monkeypatch) -> None:
    monkeypatch.setattr(system.socket, "gethostname", lambda: "test-host")
    monkeypatch.setattr(system.platform, "system", lambda: "TestOS")
    monkeypatch.setattr(system.platform, "release", lambda: "1.2.3")
    monkeypatch.setattr(system.time, "time", lambda: 1_000.0)
    monkeypatch.setattr(system.psutil, "boot_time", lambda: 100.0)
    monkeypatch.setattr(system.psutil, "cpu_percent", lambda interval: 12.5)
    monkeypatch.setattr(
        system.psutil, "virtual_memory", lambda: SimpleNamespace(percent=45.5)
    )
    monkeypatch.setattr(
        system.psutil, "disk_usage", lambda path: SimpleNamespace(percent=67.5)
    )
    monkeypatch.setattr(
        system.psutil,
        "net_if_addrs",
        lambda: {
            "lo": [SimpleNamespace(family=socket.AF_INET, address="127.0.0.1")],
            "eth0": [SimpleNamespace(family=socket.AF_INET, address="192.0.2.10")],
        },
    )

    metrics = system.collect_system_metrics()

    assert metrics.hostname == "test-host"
    assert metrics.operating_system == "TestOS 1.2.3"
    assert metrics.uptime_seconds == 900.0
    assert metrics.cpu_percent == 12.5
    assert metrics.memory_percent == 45.5
    assert metrics.disk_percent == 67.5
    assert metrics.ip_address == "192.0.2.10"


def test_primary_ip_address_is_unavailable_without_non_loopback_ipv4(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        system.psutil,
        "net_if_addrs",
        lambda: {
            "lo": [SimpleNamespace(family=socket.AF_INET, address="127.0.0.1")]
        },
    )

    assert system._primary_ip_address() == "unavailable"


def test_primary_ip_address_is_unavailable_when_access_is_denied(
    monkeypatch, caplog
) -> None:
    def deny_access():
        raise PermissionError("access denied")

    monkeypatch.setattr(system.psutil, "net_if_addrs", deny_access)

    assert system._primary_ip_address() == "unavailable"
    assert "Unable to inspect network interfaces" in caplog.text
