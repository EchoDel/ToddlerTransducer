"""
Web UI Devices

Module containing the routes for device role configuration, pairing and
syncing between a master and slave ToddlerTransducer device.
"""

import secrets
import threading
from pathlib import Path

from flask import Flask, request, send_file

from toddler_transducer.config import AUDIO_FILE_BASE_PATH
from toddler_transducer.device_config import (
    add_bound_slave,
    bind_to_master,
    clear_pairing_code,
    get_device_name,
    get_or_create_pairing_code,
    is_master,
    is_slave,
    load_device_config,
    regenerate_pairing_code,
    remove_bound_slave,
    set_role,
    unbind_from_master,
)
from toddler_transducer.device_sync.discovery import browse_masters
from toddler_transducer.device_sync.pairing import generate_token, verify_pairing_code
from toddler_transducer.device_sync.sync import (
    build_manifest,
    get_sync_status,
    http_post_json,
    run_sync_once,
)
from toddler_transducer.metadata import load_metadata


def add_device_routes(flask_app: Flask) -> None:
    """Register all device pairing and sync routes on the Flask app.

    Args:
        flask_app: Flask application instance.
    """

    def _sync_token_valid() -> bool:
        """Return whether the request carries a valid sync token."""
        provided = request.headers.get("X-Sync-Token", "")
        slaves = load_device_config().get("bound_slaves", {})
        return any(secrets.compare_digest(provided, entry["token"]) for entry in slaves.values())

    @flask_app.route("/api/devices/status")
    def api_devices_status() -> dict:
        """Return the device role, pairing state and sync status."""
        config = load_device_config()
        pairing_code = config.get("pairing_code")
        if is_master() and not pairing_code:
            pairing_code = get_or_create_pairing_code()
        return {
            "role": config.get("role", "unset"),
            "device_name": get_device_name(),
            "pairing_code": pairing_code,
            "bound_slaves": list(config.get("bound_slaves", {}).keys()),
            "master_hostname": config.get("master_hostname"),
            "master_port": config.get("master_port"),
            **get_sync_status(),
        }

    @flask_app.route("/api/devices/role", methods=["POST"])
    def api_devices_role():
        """Set the device role to master or slave."""
        data = request.get_json(silent=True) or {}
        role = data.get("role")
        if role not in ("master", "slave"):
            return {"ok": False}, 400
        set_role(role)
        return {"ok": True}

    @flask_app.route("/api/devices/pairing_code", methods=["POST"])
    def api_pairing_code():
        """Regenerate the pairing code on the master."""
        if not is_master():
            return {"ok": False}, 403
        return {"ok": True, "pairing_code": regenerate_pairing_code()}

    @flask_app.route("/api/devices/pair", methods=["POST"])
    def api_pair():
        """Accept a slave pairing request on the master."""
        if not is_master():
            return {"ok": False}, 403
        data = request.get_json(silent=True) or {}
        provided = (data.get("code") or "").strip().upper()
        device_name = (data.get("device_name") or "").strip()
        expected = load_device_config().get("pairing_code")
        if not expected or not verify_pairing_code(provided, expected):
            return {"ok": False, "error": "invalid pairing code"}, 401
        token = generate_token()
        add_bound_slave(device_name, token)
        clear_pairing_code()
        return {"ok": True, "token": token, "device_name": get_device_name()}

    @flask_app.route("/api/devices/unpair", methods=["POST"])
    def api_unpair():
        """Remove a bound slave from the master."""
        if not is_master():
            return {"ok": False}, 403
        data = request.get_json(silent=True) or {}
        device_name = data.get("device_name")
        if not device_name:
            return {"ok": False}, 400
        remove_bound_slave(device_name)
        return {"ok": True}

    @flask_app.route("/api/devices/scan", methods=["POST"])
    def api_scan():
        """Scan the local network for master devices."""
        try:
            devices = browse_masters(timeout=3.0)
        except Exception as exc:
            return {"ok": False, "devices": [], "error": str(exc)}, 500
        return {"ok": True, "devices": devices}

    @flask_app.route("/api/devices/bind", methods=["POST"])
    def api_bind():
        """Bind this slave to a discovered master using a pairing code."""
        data = request.get_json(silent=True) or {}
        hostname = (data.get("hostname") or "").strip()
        try:
            port = int(data.get("port", 8080))
        except (TypeError, ValueError):
            return {"ok": False, "error": "invalid port"}, 400
        code = (data.get("code") or "").strip()
        if not hostname or not code:
            return {"ok": False, "error": "hostname and code required"}, 400
        try:
            response = http_post_json(
                f"http://{hostname}:{port}/api/devices/pair",
                {"code": code, "device_name": get_device_name()},
            )
        except Exception as exc:
            return {"ok": False, "error": str(exc)}, 502
        if not response.get("ok"):
            return {"ok": False, "error": response.get("error", "pairing failed")}, 401
        bind_to_master(hostname, port, response["token"])
        return {"ok": True, "master_device_name": response.get("device_name")}

    @flask_app.route("/api/devices/unbind", methods=["POST"])
    def api_unbind():
        """Clear the slave binding, reverting to a master role."""
        unbind_from_master()
        return {"ok": True}

    @flask_app.route("/api/devices/sync_now", methods=["POST"])
    def api_sync_now():
        """Trigger an immediate sync pass from the master."""
        if not is_slave():
            return {"ok": False}, 400
        threading.Thread(target=run_sync_once, daemon=True).start()
        return {"ok": True}

    @flask_app.route("/api/sync/manifest")
    def api_sync_manifest():
        """Return the library manifest to a bound slave."""
        if not _sync_token_valid():
            return {"error": "unauthorized"}, 401
        return build_manifest(AUDIO_FILE_BASE_PATH)

    @flask_app.route("/api/sync/file/<uuid>")
    def api_sync_file(uuid: str):
        """Stream a single audio file to a bound slave."""
        if not _sync_token_valid():
            return {"error": "unauthorized"}, 401
        entry = load_metadata().get(uuid)
        if entry is None:
            return {"error": "not found"}, 404
        file_path = Path(AUDIO_FILE_BASE_PATH) / entry["file_name"]
        if not file_path.exists():
            return {"error": "not found"}, 404
        return send_file(file_path)
