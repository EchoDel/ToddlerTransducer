"""
Discovery

Module for advertising this device as a master and browsing for masters
on the local network using mDNS (zeroconf) so that no fixed IP addresses
are required.
"""

import socket
import time
from dataclasses import dataclass

from zeroconf import ServiceBrowser, ServiceInfo, ServiceListener, Zeroconf

SERVICE_TYPE = "_toddlertx._tcp.local."


def _decode(value) -> str:
    """Decode a zeroconf TXT value which may be bytes or str."""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _local_addresses() -> list[bytes]:
    """Return the non-loopback IPv4 addresses for this host.

    Returns:
        list[bytes]: The packed addresses, which may be empty if none resolve.
    """
    addresses: list[bytes] = []
    try:
        for addr in socket.getaddrinfo(socket.gethostname(), None):
            candidate = addr[4][0]
            if isinstance(candidate, str) and ":" not in candidate and not candidate.startswith("127."):
                try:
                    addresses.append(socket.inet_aton(candidate))
                except OSError:
                    pass
    except socket.gaierror:
        pass
    return addresses


def advertise(port: int, device_name: str) -> Zeroconf:
    """Register this device as a master service on the local network.

    Args:
        port (int): The web UI port to advertise.
        device_name (str): The friendly device name.

    Returns:
        Zeroconf: The zeroconf instance which must be kept alive.
    """
    hostname = socket.gethostname()
    server = f"{hostname}.local."
    info = ServiceInfo(
        SERVICE_TYPE,
        f"{hostname}.{SERVICE_TYPE}",
        server=server,
        port=port,
        addresses=_local_addresses() or None,
        properties={"role": "master", "device_name": device_name},
    )
    zc = Zeroconf()
    try:
        zc.register_service(info)
    except Exception:
        zc.close()
        raise
    return zc


@dataclass
class DiscoveredMaster:
    """A master device discovered on the local network."""

    device_name: str
    hostname: str
    port: int


class _MasterListener(ServiceListener):
    """Collects master services discovered on the local network."""

    def __init__(self, masters: list[dict]) -> None:
        self.masters = masters

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        info = zc.get_service_info(type_, name)
        if info is None:
            return
        if _decode(info.properties.get(b"role", b"")) != "master":
            return
        hostname = info.server or f"{name.split('.')[0]}.local."
        self.masters.append(
            {
                "device_name": _decode(info.properties.get(b"device_name", name)),
                "hostname": hostname,
                "port": info.port,
            }
        )

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        pass

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        pass


def browse_masters(timeout: float = 3.0) -> list[dict]:
    """Browse the local network for master devices.

    Args:
        timeout (float): Seconds to wait for discovery to complete.

    Returns:
        list[dict]: The discovered masters with device_name, hostname and port.
    """
    masters: list[dict] = []
    zc = Zeroconf()
    try:
        ServiceBrowser(zc, SERVICE_TYPE, _MasterListener(masters))
        time.sleep(timeout)
    finally:
        zc.close()
    return masters
