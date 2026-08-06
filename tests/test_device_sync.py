import hashlib
import json
from pathlib import Path

import pytest

from toddler_transducer.device_sync.pairing import (
    PAIRING_ALPHABET,
    generate_pairing_code,
    generate_token,
    verify_pairing_code,
)
from toddler_transducer.device_config import bind_to_master, unbind_from_master
from toddler_transducer.device_sync import sync as sync_module
from toddler_transducer.device_sync.sync import apply_manifest, build_manifest, run_sync_once
from toddler_transducer.metadata import append_to_metadata


@pytest.fixture(autouse=True)
def reset_sync_state():
    """Reset module-level sync state between tests."""
    sync_module._last_revision = None
    sync_module._last_sync_target = None
    yield


class TestPairing:
    def test_generate_pairing_code_format(self):
        code = generate_pairing_code()
        assert len(code) == 6
        assert set(code) <= set(PAIRING_ALPHABET)

    def test_verify_case_insensitive(self):
        code = generate_pairing_code()
        assert verify_pairing_code(code, code.lower())
        assert not verify_pairing_code(code, "XXXXXX")

    def test_generate_token_length(self):
        assert len(generate_token()) == 64


class TestBuildManifest:
    def test_manifest_matches_metadata(self, tmp_audio_root: Path):
        manifest = build_manifest()
        assert len(manifest["songs"]) == 2
        entry = manifest["songs"]["abc-123"]
        assert entry["file_name"] == "abc-123.ogg"
        assert entry["rfid_id"] == 1001
        assert entry["track_name"] == "Test Track 1"
        assert entry["size"] == len(b"fake-audio-data")
        assert entry["sha256"] == hashlib.sha256(b"fake-audio-data").hexdigest()
        assert len(manifest["revision"]) == 64

    def test_manifest_skips_missing_files(self, tmp_audio_root: Path):
        (tmp_audio_root / "abc-123.ogg").unlink()
        manifest = build_manifest()
        assert "abc-123" not in manifest["songs"]

    def test_revision_changes_when_library_changes(self, tmp_audio_root: Path):
        first = build_manifest()["revision"]
        append_to_metadata("xyz", "xyz.wav", 2001, "New Track")
        (tmp_audio_root / "xyz.wav").write_bytes(b"x" * 10)
        second = build_manifest()["revision"]
        assert first != second


class TestApplyManifest:
    def _manifest(self, uuid="aaa", name="aaa.ogg", content=b"abc"):
        return {
            "revision": "rev",
            "songs": {
                uuid: {
                    "file_name": name,
                    "rfid_id": 1,
                    "track_name": "A",
                    "size": len(content),
                    "sha256": hashlib.sha256(content).hexdigest(),
                },
            },
        }

    def test_downloads_missing_files(self, tmp_path: Path):
        dest = tmp_path / "audio"
        dest.mkdir()
        calls = []

        def fetch(uuid):
            calls.append(uuid)
            return b"abc"

        result = apply_manifest(self._manifest(), dest, fetch)
        assert calls == ["aaa"]
        assert (dest / "aaa.ogg").read_bytes() == b"abc"
        assert result["downloaded"] == 1
        assert result["unchanged"] == 0
        metadata = json.loads((dest / "metadata").read_text())
        assert metadata["aaa"]["track_name"] == "A"
        assert metadata["aaa"]["rfid_id"] == 1

    def test_noop_when_unchanged(self, tmp_path: Path):
        dest = tmp_path / "audio"
        dest.mkdir()
        (dest / "aaa.ogg").write_bytes(b"abc")
        calls = []

        def fetch(uuid):
            calls.append(uuid)
            return b"abc"

        result = apply_manifest(self._manifest(), dest, fetch)
        assert calls == []
        assert result["downloaded"] == 0
        assert result["unchanged"] == 1

    def test_deletes_orphans(self, tmp_path: Path):
        dest = tmp_path / "audio"
        dest.mkdir()
        (dest / "aaa.ogg").write_bytes(b"abc")
        (dest / "orphan.mp3").write_bytes(b"zzz")
        result = apply_manifest(self._manifest(), dest, lambda uuid: b"abc")
        assert result["deleted"] == 1
        assert not (dest / "orphan.mp3").exists()
        assert (dest / "aaa.ogg").exists()

    def test_keeps_metadata_file(self, tmp_path: Path):
        dest = tmp_path / "audio"
        dest.mkdir()
        (dest / "metadata").write_text("{}")
        (dest / "aaa.ogg").write_bytes(b"abc")
        apply_manifest(self._manifest(), dest, lambda uuid: b"abc")
        assert (dest / "metadata").exists()

    def test_checksum_mismatch_raises(self, tmp_path: Path):
        dest = tmp_path / "audio"
        dest.mkdir()
        manifest = self._manifest(content=b"abc")
        manifest["songs"]["aaa"]["sha256"] = "deadbeef"
        with pytest.raises(ValueError):
            apply_manifest(manifest, dest, lambda uuid: b"xyz")

    def test_invalid_manifest_raises(self, tmp_path: Path):
        dest = tmp_path / "audio"
        dest.mkdir()
        with pytest.raises(ValueError):
            apply_manifest({"revision": "rev"}, dest, lambda uuid: b"")


class TestRunSyncOnce:
    def test_noop_when_not_slave(self, monkeypatch):
        calls = []
        monkeypatch.setattr(
            "toddler_transducer.device_sync.sync.http_get_json", lambda *a, **k: calls.append("x")
        )
        run_sync_once()
        assert calls == []

    def test_noop_when_unbound(self, monkeypatch):
        bind_to_master("master.local", 8080, "tok")
        unbind_from_master()
        calls = []
        monkeypatch.setattr(
            "toddler_transducer.device_sync.sync.http_get_json", lambda *a, **k: calls.append("x")
        )
        run_sync_once()
        assert calls == []

    def test_applies_only_when_revision_changes(self, monkeypatch):
        bind_to_master("master.local", 8080, "tok")
        applied = []
        fake_manifest = {"revision": "rev-1", "songs": {}}
        monkeypatch.setattr(
            "toddler_transducer.device_sync.sync.http_get_json", lambda *a, **k: fake_manifest
        )
        monkeypatch.setattr(
            "toddler_transducer.device_sync.sync.apply_manifest",
            lambda *a, **k: applied.append(a),
        )
        run_sync_once()
        assert len(applied) == 1
        run_sync_once()
        assert len(applied) == 1

    def test_resets_revision_after_unbind(self, monkeypatch):
        bind_to_master("master.local", 8080, "tok")
        applied = []
        fake_manifest = {"revision": "rev-1", "songs": {}}
        monkeypatch.setattr(
            "toddler_transducer.device_sync.sync.http_get_json", lambda *a, **k: fake_manifest
        )
        monkeypatch.setattr(
            "toddler_transducer.device_sync.sync.apply_manifest",
            lambda *a, **k: applied.append(a),
        )
        run_sync_once()
        assert len(applied) == 1
        unbind_from_master()
        bind_to_master("master2.local", 8080, "tok2")
        run_sync_once()
        assert len(applied) == 2
