"""
Device Config

Module for reading and writing the local device configuration which
controls whether this device is the master (song library) or a slave
(mirror) and, for slaves, how to reach the master.
"""

import json
import socket
from typing import Literal, TypedDict

from toddler_transducer.config import DEVICE_CONFIG_FILE_PATH
from toddler_transducer.device_sync.pairing import generate_pairing_code


class BoundSlave(TypedDict):
    """A slave bound to this master, keyed by the token it must present."""

    token: str


class DeviceConfig(TypedDict, total=False):
    """The device configuration persisted to disk."""

    role: Literal["master", "slave"]
    device_name: str
    pairing_code: str
    bound_slaves: dict[str, BoundSlave]
    master_hostname: str
    master_port: int
    token: str
    last_synced: str
    last_error: str
    song_count: int


def load_device_config() -> DeviceConfig:
    """Load the device configuration from disk.

    Returns:
        DeviceConfig: The device configuration, or an empty dict if missing.
    """
    if DEVICE_CONFIG_FILE_PATH.exists():
        try:
            return json.loads(DEVICE_CONFIG_FILE_PATH.read_text(encoding="UTF-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_device_config(config: DeviceConfig) -> None:
    """Persist the device configuration to disk.

    Args:
        config (DeviceConfig): The device configuration to save.
    """
    DEVICE_CONFIG_FILE_PATH.write_text(json.dumps(config, indent=2), encoding="UTF-8")


def get_device_name() -> str:
    """Return the friendly device name, falling back to the hostname.

    Returns:
        str: The device name.
    """
    config = load_device_config()
    return config.get("device_name") or socket.gethostname() or "toddler-transducer"


def is_master() -> bool:
    """Return whether this device is configured as the master library.

    Returns:
        bool: True if this device is the master.
    """
    return load_device_config().get("role") == "master"


def is_slave() -> bool:
    """Return whether this device is configured as a slave mirror.

    Returns:
        bool: True if this device is a slave.
    """
    return load_device_config().get("role") == "slave"


def set_role(role: Literal["master", "slave"]) -> None:
    """Set the device role, clearing the other role's fields.

    Args:
        role (Literal['master', 'slave']): The new role.
    """
    config = load_device_config()
    config["role"] = role
    config["device_name"] = config.get("device_name") or get_device_name()
    if role == "master":
        config.pop("master_hostname", None)
        config.pop("master_port", None)
        config.pop("token", None)
    else:
        config.pop("pairing_code", None)
        config.pop("bound_slaves", None)
    save_device_config(config)


def add_bound_slave(device_name: str, token: str) -> None:
    """Register a bound slave on the master with its sync token.

    Args:
        device_name (str): The name of the slave device.
        token (str): The token issued to the slave.
    """
    config = load_device_config()
    config["role"] = "master"
    config.setdefault("bound_slaves", {})[device_name] = {"token": token}
    save_device_config(config)


def remove_bound_slave(device_name: str) -> None:
    """Remove a bound slave from the master.

    Args:
        device_name (str): The name of the slave device to remove.
    """
    config = load_device_config()
    config.get("bound_slaves", {}).pop(device_name, None)
    save_device_config(config)


def get_or_create_pairing_code() -> str:
    """Return the existing pairing code, generating one if absent.

    Returns:
        str: The pairing code.
    """
    config = load_device_config()
    code = config.get("pairing_code")
    if not code:
        code = generate_pairing_code()
        config["pairing_code"] = code
        save_device_config(config)
    return code


def regenerate_pairing_code() -> str:
    """Generate and persist a fresh pairing code.

    Returns:
        str: The new pairing code.
    """
    config = load_device_config()
    code = generate_pairing_code()
    config["pairing_code"] = code
    save_device_config(config)
    return code


def clear_pairing_code() -> None:
    """Remove the pairing code so it cannot be reused."""
    config = load_device_config()
    config.pop("pairing_code", None)
    save_device_config(config)


def bind_to_master(hostname: str, port: int, token: str) -> None:
    """Store the master connection details on a slave device.

    Args:
        hostname (str): The hostname of the master device.
        port (int): The web UI port of the master device.
        token (str): The sync token issued by the master.
    """
    config = load_device_config()
    config["role"] = "slave"
    config["device_name"] = config.get("device_name") or get_device_name()
    config["master_hostname"] = hostname
    config["master_port"] = int(port) if port is not None else 8080
    config["token"] = token
    config.pop("pairing_code", None)
    config.pop("bound_slaves", None)
    save_device_config(config)


def unbind_from_master() -> None:
    """Clear the master connection, reverting the device to a master role."""
    config = load_device_config()
    config.pop("master_hostname", None)
    config.pop("master_port", None)
    config.pop("token", None)
    if config.get("role") == "slave":
        config["role"] = "master"
    save_device_config(config)


def get_master_target() -> tuple[str, int] | None:
    """Return the configured master address for a slave.

    Returns:
        tuple[str, int] | None: The master hostname and port, or None.
    """
    config = load_device_config()
    if config.get("role") != "slave":
        return None
    hostname = config.get("master_hostname")
    if not hostname:
        return None
    return hostname, int(config.get("master_port", 8080))


def get_sync_token() -> str | None:
    """Return the sync token for a slave device.

    Returns:
        str | None: The sync token, or None if not a slave.
    """
    config = load_device_config()
    if config.get("role") != "slave":
        return None
    return config.get("token")


def update_sync_status(
    last_synced: str | None = None, last_error: str | None = None, song_count: int | None = None
) -> None:
    """Persist the latest sync status to the device configuration.

    Args:
        last_synced (str | None): ISO timestamp of the last successful sync.
        last_error (str | None): Message of the last sync error, if any.
        song_count (int | None): Number of songs in the synced library.
    """
    config = load_device_config()
    if last_synced is not None:
        config["last_synced"] = last_synced
    if last_error is not None:
        config["last_error"] = last_error
    if song_count is not None:
        config["song_count"] = song_count
    save_device_config(config)
