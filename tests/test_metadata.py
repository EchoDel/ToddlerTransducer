import json
from pathlib import Path

import pytest

from toddler_transducer.metadata import load_metadata, save_metadata, append_to_metadata, remove_from_metadata, remove_from_metadata_by_track_name, METADATA


class TestLoadMetadata:
    def test_load_existing(self, tmp_audio_root: Path):
        meta = load_metadata()
        assert 'abc-123' in meta
        assert meta['abc-123']['track_name'] == 'Test Track 1'

    def test_load_missing_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        missing = tmp_path / 'no_metadata'
        monkeypatch.setattr('toddler_transducer.metadata.METADATA_FILE_PATH', missing)
        assert load_metadata() == {}

    def test_load_empty_file(self, tmp_audio_root: Path, monkeypatch: pytest.MonkeyPatch):
        empty = tmp_audio_root / 'metadata'
        empty.write_text('')
        monkeypatch.setattr('toddler_transducer.metadata.METADATA_FILE_PATH', empty)
        with pytest.raises(json.JSONDecodeError):
            load_metadata()


class TestSaveMetadata:
    def test_save_preserves_data(self, tmp_audio_root: Path):
        meta = load_metadata()
        meta['new-uuid'] = {'file_name': 'new.ogg', 'rfid_id': 2000, 'track_name': 'New Track'}
        save_metadata(meta)
        reloaded = load_metadata()
        assert 'new-uuid' in reloaded
        assert reloaded['new-uuid']['track_name'] == 'New Track'

    def test_save_creates_backup(self, tmp_audio_root: Path):
        meta = load_metadata()
        save_metadata(meta)
        backups = list(tmp_audio_root.glob('metadata_*'))
        assert len(backups) >= 1


class TestAppendToMetadata:
    def test_appends_new_entry(self, tmp_audio_root: Path):
        append_to_metadata('ghi-789', 'ghi-789.wav', 3000, 'Third Track')
        meta = load_metadata()
        assert 'ghi-789' in meta
        assert meta['ghi-789']['rfid_id'] == 3000

    def test_does_not_duplicate_uuids(self, tmp_audio_root: Path):
        append_to_metadata('abc-123', 'new.ogg', 9999, 'Duplicate UUID')
        meta = load_metadata()
        assert meta['abc-123']['rfid_id'] == 9999


class TestRemoveFromMetadata:
    def test_remove_existing_uuid(self, tmp_audio_root: Path):
        removed = remove_from_metadata('abc-123')
        assert removed == {'file_name': 'abc-123.ogg', 'rfid_id': 1001, 'track_name': 'Test Track 1'}
        meta = load_metadata()
        assert 'abc-123' not in meta

    def test_remove_nonexistent_uuid(self, tmp_audio_root: Path):
        removed = remove_from_metadata('nonexistent')
        assert removed is None

    def test_remove_by_track_name(self, tmp_audio_root: Path):
        removed = remove_from_metadata_by_track_name('Test Track 2')
        assert removed is not None
        assert removed['track_name'] == 'Test Track 2'
        assert 'uuid' in removed
        meta = load_metadata()
        assert 'def-456' not in meta

    def test_remove_by_track_name_not_found(self, tmp_audio_root: Path):
        removed = remove_from_metadata_by_track_name('No Such Track')
        assert removed is None


class TestMetadataConstant:
    def test_metada_constant_is_populated(self):
        assert isinstance(METADATA, dict)
