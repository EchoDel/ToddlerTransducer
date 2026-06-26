import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from toddler_transducer.audio_file_manager import (
    get_current_files,
    load_backup_metadata,
    save_backup_metadata,
    delete_old_backups,
    get_sorted_backup_item,
    backup_audio_files,
)


class TestGetCurrentFiles:
    def test_returns_track_name_to_filename_map(self, tmp_audio_root: Path):
        files = get_current_files()
        assert files == {
            'Test Track 1': 'abc-123.ogg',
            'Test Track 2': 'def-456.mp3',
        }


class TestBackupMetadata:
    def test_save_and_load_round_trip(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        backup_root = tmp_path / 'backups'
        backup_root.mkdir(exist_ok=True)
        monkeypatch.setattr('toddler_transducer.audio_file_manager.BACKUP_FILE_BASE_PATH', backup_root)
        now = datetime(2025, 6, 1, 12, 0, 0)
        data = {now: str(backup_root / 'backup_20250601120000.zip')}
        save_backup_metadata(data)
        loaded = load_backup_metadata()
        assert loaded == data

    def test_load_missing_returns_empty(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        backup_root = tmp_path / 'backups'
        backup_root.mkdir(exist_ok=True)
        monkeypatch.setattr('toddler_transducer.audio_file_manager.BACKUP_FILE_BASE_PATH', backup_root)
        assert load_backup_metadata() == {}


class TestDeleteOldBackups:
    def test_delete_removes_files_and_marks_none(self, tmp_path: Path):
        backup_root = tmp_path / 'backups'
        backup_root.mkdir(exist_ok=True)
        old_file = backup_root / 'old_backup.zip'
        old_file.write_text('data')
        prior = {datetime(2024, 1, 1): str(old_file)}
        to_delete = {datetime(2024, 1, 1): str(old_file)}
        result = delete_old_backups(to_delete, prior)
        assert not old_file.exists()
        assert list(result.values()) == [None]

    def test_delete_skips_missing_files(self):
        to_delete = {datetime(2024, 1, 1): '/nonexistent/file.zip'}
        prior = {datetime(2024, 1, 1): '/nonexistent/file.zip'}
        with pytest.raises(FileNotFoundError):
            delete_old_backups(to_delete, prior)


class TestGetSortedBackupItem:
    def test_returns_most_recent(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        backup_root = tmp_path / 'backups'
        backup_root.mkdir(exist_ok=True)
        monkeypatch.setattr('toddler_transducer.audio_file_manager.BACKUP_FILE_BASE_PATH', backup_root)
        now = datetime.now().replace(microsecond=0)
        older = now - timedelta(days=2)
        data = {
            older: str(backup_root / 'old.zip'),
            now: str(backup_root / 'new.zip'),
        }
        save_backup_metadata(data)
        result = get_sorted_backup_item(-1)
        assert list(result.keys())[0] == now
        assert list(result.values())[0] == str(backup_root / 'new.zip')

    def test_returns_oldest(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        backup_root = tmp_path / 'backups'
        backup_root.mkdir(exist_ok=True)
        monkeypatch.setattr('toddler_transducer.audio_file_manager.BACKUP_FILE_BASE_PATH', backup_root)
        now = datetime.now().replace(microsecond=0)
        older = now - timedelta(days=2)
        data = {
            older: str(backup_root / 'old.zip'),
            now: str(backup_root / 'new.zip'),
        }
        save_backup_metadata(data)
        result = get_sorted_backup_item(1)
        assert list(result.keys())[0] == older
        assert list(result.values())[0] == str(backup_root / 'old.zip')


class TestBackupAudioFiles:
    def test_backup_creates_zip_and_metadata(self, tmp_audio_root: Path, tmp_path: Path,
                                              monkeypatch: pytest.MonkeyPatch):
        backup_root = tmp_path / 'backups'
        backup_root.mkdir(exist_ok=True)
        monkeypatch.setattr('toddler_transducer.audio_file_manager.BACKUP_FILE_BASE_PATH', backup_root)
        monkeypatch.setattr('toddler_transducer.audio_file_manager.AUDIO_FILE_BASE_PATH', tmp_audio_root)
        backup_audio_files()
        zips = list(backup_root.glob('*.zip'))
        assert len(zips) >= 1
        meta = load_backup_metadata()
        assert len(meta) == 1

    def test_backup_prunes_old_entries(self, tmp_audio_root: Path, tmp_path: Path,
                                        monkeypatch: pytest.MonkeyPatch):
        backup_root = tmp_path / 'backups'
        backup_root.mkdir(exist_ok=True)
        monkeypatch.setattr('toddler_transducer.audio_file_manager.BACKUP_FILE_BASE_PATH', backup_root)
        monkeypatch.setattr('toddler_transducer.audio_file_manager.AUDIO_FILE_BASE_PATH', tmp_audio_root)
        old_date = datetime.now() - timedelta(days=30)
        old_data = {
            old_date: str(backup_root / 'backup_old.zip'),
            old_date - timedelta(hours=1): str(backup_root / 'backup_older.zip'),
            old_date - timedelta(days=7): str(backup_root / 'backup_oldest.zip'),
        }
        Path(old_data[old_date]).write_text('old')
        Path(old_data[old_date - timedelta(hours=1)]).write_text('older')
        Path(old_data[old_date - timedelta(days=7)]).write_text('oldest')
        save_backup_metadata({k: v for k, v in old_data.items()})
        backup_audio_files()
        meta = load_backup_metadata()
        assert len(meta) <= 7


class TestGetCurrentFilesIntegration:
    def test_returns_correct_names_from_real_metadata(self, tmp_audio_root: Path):
        files = get_current_files()
        assert 'Test Track 1' in files
        assert files['Test Track 1'] == 'abc-123.ogg'
