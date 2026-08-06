"""End-to-end sync tests between a running master web app and a slave."""

import json
import threading
from pathlib import Path

import pytest
from werkzeug.serving import make_server


def _reset_sync_state(sync_module) -> None:
    sync_module._last_revision = None
    sync_module._last_sync_target = None


def _start_server(flask_app):
    """Serve the Flask app on an ephemeral port, returning (server, port)."""
    server = make_server("127.0.0.1", 0, flask_app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, server.server_port


@pytest.fixture
def slave_audio(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A separate audio directory acting as the slave's local library."""
    slave_dir = tmp_path / "slave_audio"
    slave_dir.mkdir(parents=True)
    monkeypatch.setattr("toddler_transducer.device_sync.sync.AUDIO_FILE_BASE_PATH", slave_dir)
    return slave_dir


def test_slave_mirrors_master_library(flask_app, tmp_audio_root: Path, slave_audio: Path, monkeypatch):
    """A slave bound to a live master downloads songs and metadata over HTTP."""
    from toddler_transducer.device_config import save_device_config
    from toddler_transducer.device_sync import sync as sync_module

    server, port = _start_server(flask_app)
    try:
        config = {
            "role": "slave",
            "device_name": "slave-test",
            "master_hostname": "127.0.0.1",
            "master_port": port,
            "token": "test-token",
            "bound_slaves": {"slave-test": {"token": "test-token"}},
        }
        save_device_config(config)
        _reset_sync_state(sync_module)
        sync_module.run_sync_once()

        assert (slave_audio / "abc-123.ogg").read_text() == "fake-audio-data"
        assert (slave_audio / "def-456.mp3").read_text() == "fake-audio-data-mp3"
        slave_metadata = json.loads((slave_audio / "metadata").read_text(encoding="UTF-8"))
        assert slave_metadata == {
            "abc-123": {"file_name": "abc-123.ogg", "rfid_id": 1001, "track_name": "Test Track 1"},
            "def-456": {"file_name": "def-456.mp3", "rfid_id": 1002, "track_name": "Test Track 2"},
        }

        (tmp_audio_root / "abc-123.ogg").write_text("updated-audio-data")
        _reset_sync_state(sync_module)
        sync_module.run_sync_once()
        assert (slave_audio / "abc-123.ogg").read_text() == "updated-audio-data"
    finally:
        server.shutdown()


def test_slave_removes_orphaned_songs(flask_app, tmp_audio_root: Path, slave_audio: Path):
    """Songs deleted on the master are removed from the slave on the next sync."""
    from toddler_transducer.device_config import save_device_config
    from toddler_transducer.device_sync import sync as sync_module

    server, port = _start_server(flask_app)
    try:
        save_device_config(
            {
                "role": "slave",
                "device_name": "slave-test",
                "master_hostname": "127.0.0.1",
                "master_port": port,
                "token": "test-token",
                "bound_slaves": {"slave-test": {"token": "test-token"}},
            }
        )
        _reset_sync_state(sync_module)
        sync_module.run_sync_once()
        assert (slave_audio / "abc-123.ogg").exists()

        metadata_path = tmp_audio_root / "metadata"
        metadata = json.loads(metadata_path.read_text(encoding="UTF-8"))
        del metadata["abc-123"]
        metadata_path.write_text(json.dumps(metadata), encoding="UTF-8")
        (tmp_audio_root / "abc-123.ogg").unlink()

        _reset_sync_state(sync_module)
        sync_module.run_sync_once()
        assert not (slave_audio / "abc-123.ogg").exists()
        assert (slave_audio / "def-456.mp3").exists()
        slave_metadata = json.loads((slave_audio / "metadata").read_text(encoding="UTF-8"))
        assert "abc-123" not in slave_metadata
    finally:
        server.shutdown()


def test_slave_rejects_unauthorized_manifest(flask_app, tmp_audio_root: Path, slave_audio: Path):
    """A manifest request without a valid token is rejected with 401."""
    from toddler_transducer.device_config import save_device_config
    from toddler_transducer.device_sync import sync as sync_module

    server, port = _start_server(flask_app)
    try:
        save_device_config(
            {
                "role": "slave",
                "device_name": "slave-test",
                "master_hostname": "127.0.0.1",
                "master_port": port,
                "token": "wrong-token",
                "bound_slaves": {"slave-test": {"token": "test-token"}},
            }
        )
        _reset_sync_state(sync_module)
        with pytest.raises(Exception):
            sync_module.run_sync_once()
        assert not (slave_audio / "abc-123.ogg").exists()
    finally:
        server.shutdown()
