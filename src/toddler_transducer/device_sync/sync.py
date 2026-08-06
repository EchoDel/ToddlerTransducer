"""
Sync

Module for building a manifest of the master's library and applying it
to a slave device, including the background polling thread which keeps
the slave in sync with the master over HTTP.
"""

import hashlib
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from toddler_transducer.config import AUDIO_FILE_BASE_PATH
from toddler_transducer.device_config import (
    get_master_target,
    get_sync_token,
    is_slave,
    update_sync_status,
)
from toddler_transducer.metadata import load_metadata

SYNC_POLL_INTERVAL_SECONDS = 30

_sha256_cache: dict[tuple[str, int, int], str] = {}
_last_revision: str | None = None
_last_sync_target: tuple[str, int] | None = None
_sync_status: dict[str, str | int | None] = {
    "last_synced": None,
    "last_error": None,
    "song_count": 0,
}


def _file_sha256(file_path: Path) -> str:
    """Return the SHA-256 of a file, caching by (path, size, mtime)."""
    stat = file_path.stat()
    cache_key = (str(file_path), stat.st_size, stat.st_mtime_ns)
    cached = _sha256_cache.get(cache_key)
    if cached is not None:
        return cached
    digest = hashlib.sha256(file_path.read_bytes()).hexdigest()
    _sha256_cache[cache_key] = digest
    return digest


def build_manifest(base_path: Path | None = None) -> dict:
    """Build the library manifest for the master's current metadata.

    Args:
        base_path (Path | None): The audio files directory, defaults to config.

    Returns:
        dict: The manifest with a revision hash and song entries.
    """
    base = base_path or AUDIO_FILE_BASE_PATH
    metadata = load_metadata()
    songs: dict[str, dict] = {}
    for uuid, entry in metadata.items():
        file_path = base / entry["file_name"]
        if not file_path.is_file():
            continue
        songs[uuid] = {
            "file_name": entry["file_name"],
            "rfid_id": entry["rfid_id"],
            "track_name": entry["track_name"],
            "size": file_path.stat().st_size,
            "sha256": _file_sha256(file_path),
        }
    revision_payload = {
        uuid: (song["file_name"], song["rfid_id"], song["track_name"], song["size"]) for uuid, song in songs.items()
    }
    revision = hashlib.sha256(json.dumps(revision_payload, sort_keys=True).encode()).hexdigest()
    return {"revision": revision, "songs": songs}


def apply_manifest(manifest: dict, base_path: Path, fetch_file) -> dict:
    """Make the local audio directory match the master's manifest.

    Args:
        manifest (dict): The manifest returned by the master.
        base_path (Path): The local audio files directory.
        fetch_file: Callable taking a uuid and returning the file bytes.

    Returns:
        dict: Counts of downloaded, deleted and unchanged files.

    Raises:
        ValueError: If a downloaded file fails its checksum.
    """
    if "songs" not in manifest:
        raise ValueError("Invalid manifest")
    base_path = Path(base_path)
    songs = manifest["songs"]
    metadata: dict[str, dict] = {}
    desired_names: set[str] = set()
    downloaded = 0
    deleted = 0
    unchanged = 0
    for uuid, entry in songs.items():
        name = entry["file_name"]
        desired_names.add(name)
        metadata[uuid] = {
            "file_name": name,
            "rfid_id": entry["rfid_id"],
            "track_name": entry["track_name"],
        }
        file_path = base_path / name
        if file_path.is_file() and file_path.stat().st_size == entry["size"]:
            unchanged += 1
            continue
        data = fetch_file(uuid)
        if hashlib.sha256(data).hexdigest() != entry["sha256"]:
            raise ValueError(f"Checksum mismatch for {name}")
        file_path.write_bytes(data)
        downloaded += 1

    for path in base_path.iterdir():
        if path.is_file() and path.name != "metadata" and path.name not in desired_names:
            path.unlink()
            deleted += 1

    (base_path / "metadata").write_text(json.dumps(metadata), encoding="UTF-8")
    return {"downloaded": downloaded, "deleted": deleted, "unchanged": unchanged}


def _urlopen(url: str, token: str | None, timeout: int):
    headers = {"X-Sync-Token": token} if token else {}
    request = urllib.request.Request(url, headers=headers)
    return urllib.request.urlopen(request, timeout=timeout)


def http_get_json(url: str, token: str | None = None, timeout: int = 15) -> dict:
    """Perform an authenticated GET returning JSON.

    Args:
        url (str): The URL to fetch.
        token (str | None): The sync token to send.
        timeout (int): The request timeout in seconds.

    Returns:
        dict: The parsed JSON response.
    """
    with _urlopen(url, token, timeout) as response:
        return json.loads(response.read().decode("UTF-8"))


def http_get_bytes(url: str, token: str | None = None, timeout: int = 120) -> bytes:
    """Perform an authenticated GET returning raw bytes.

    Args:
        url (str): The URL to fetch.
        token (str | None): The sync token to send.
        timeout (int): The request timeout in seconds.

    Returns:
        bytes: The response body.
    """
    with _urlopen(url, token, timeout) as response:
        return response.read()


def http_post_json(url: str, payload: dict, timeout: int = 15) -> dict:
    """Perform a POST with a JSON body returning JSON.

    Args:
        url (str): The URL to post to.
        payload (dict): The JSON payload.
        timeout (int): The request timeout in seconds.

    Returns:
        dict: The parsed JSON response.
    """
    data = json.dumps(payload).encode("UTF-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("UTF-8"))


def _now_iso() -> str:
    """Return the current UTC time as an ISO string."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_sync_status() -> dict[str, str | int | None]:
    """Return the current sync status.

    Returns:
        dict: last_synced, last_error and song_count.
    """
    return dict(_sync_status)


def run_sync_once() -> None:
    """Perform a single sync pass from the master to this slave."""
    global _last_revision, _last_sync_target
    if not is_slave():
        _last_revision = None
        _last_sync_target = None
        return
    target = get_master_target()
    token = get_sync_token()
    if not target or not token:
        _last_revision = None
        _last_sync_target = None
        return
    if target != _last_sync_target:
        _last_sync_target = target
        _last_revision = None
    base_url = f"http://{target[0]}:{target[1]}"
    manifest = http_get_json(f"{base_url}/api/sync/manifest", token)
    revision = manifest.get("revision")
    song_count = len(manifest.get("songs", {}))
    if revision == _last_revision:
        update_sync_status(last_synced=_now_iso(), last_error=None, song_count=song_count)
        _sync_status.update(last_synced=_now_iso(), last_error=None, song_count=song_count)
        return

    def fetch(uuid: str) -> bytes:
        return http_get_bytes(f"{base_url}/api/sync/file/{uuid}", token)

    apply_manifest(manifest, AUDIO_FILE_BASE_PATH, fetch)
    _last_revision = revision
    update_sync_status(last_synced=_now_iso(), last_error=None, song_count=song_count)
    _sync_status.update(last_synced=_now_iso(), last_error=None, song_count=song_count)


def sync_loop_thread() -> None:
    """Background thread which polls the master and applies changes."""
    while True:
        try:
            run_sync_once()
        except Exception as exc:
            _sync_status["last_error"] = str(exc)
            update_sync_status(last_error=str(exc))
        time.sleep(SYNC_POLL_INTERVAL_SECONDS)
