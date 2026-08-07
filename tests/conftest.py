import os
import sys
import json
import copy
from pathlib import Path
from unittest.mock import MagicMock, patch
from multiprocessing.managers import DictProxy

import pytest


def pytest_configure():
    """Install fake RPi.GPIO and mfrc522 modules before ANY toddler_transducer
    import so that module-level code in gpio.py etc. sees the fakes."""
    import toddler_transducer.proxies.fake_raspberry_pi as fake_rpi
    sys.modules.setdefault('RPi', fake_rpi)
    sys.modules.setdefault('RPi.GPIO', fake_rpi.GPIO)


BASE_VLC_STATE = {
    'play_rfid_id': False,
    'play_track_name': False,
    'do_play': False,
    'do_stop': False,
    'do_pause': False,
    'toggle_looping': False,
    'seek_position': -1.0,
    'volume': 50,
    'puck_lockout': False,
    'playback_source': None,
    'is_playing': False,
    'is_looping': False,
    'current_playing_track_uuid': None,
    'track_length': 0.0,
    'track_time_through': 0.0,
}


@pytest.fixture
def tmp_audio_root(tmp_path: Path) -> Path:
    """Create a temporary audio_files directory with dummy metadata."""
    audio_root = tmp_path / 'audio_files'
    audio_root.mkdir(parents=True, exist_ok=True)
    meta = {
        "abc-123": {
            "file_name": "abc-123.ogg",
            "rfid_id": 1001,
            "track_name": "Test Track 1",
        },
        "def-456": {
            "file_name": "def-456.mp3",
            "rfid_id": 1002,
            "track_name": "Test Track 2",
        },
    }
    (audio_root / 'metadata').write_text(json.dumps(meta))
    (audio_root / 'abc-123.ogg').write_text("fake-audio-data")
    (audio_root / 'def-456.mp3').write_text("fake-audio-data-mp3")
    return audio_root


@pytest.fixture(autouse=True)
def patch_config(tmp_audio_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Point config paths at temp locations so no real filesystem is touched."""
    monkeypatch.setattr('toddler_transducer.config.AUDIO_FILE_BASE_PATH', tmp_audio_root)
    monkeypatch.setattr('toddler_transducer.config.METADATA_FILE_PATH', tmp_audio_root / 'metadata')
    monkeypatch.setattr('toddler_transducer.config.BACKUP_FILE_BASE_PATH', tmp_path / 'backups')
    monkeypatch.setattr('toddler_transducer.config.VOLUME_FILE_PATH', tmp_path / 'persistent_settings.json')
    monkeypatch.setattr('toddler_transducer.metadata.METADATA_FILE_PATH', tmp_audio_root / 'metadata')
    monkeypatch.setattr('toddler_transducer.audio.AUDIO_FILE_BASE_PATH', tmp_audio_root)
    monkeypatch.setattr('toddler_transducer.audio.VOLUME_FILE_PATH', tmp_path / 'persistent_settings.json')
    monkeypatch.setattr('toddler_transducer.audio_file_manager.AUDIO_FILE_BASE_PATH', tmp_audio_root)
    monkeypatch.setattr('toddler_transducer.audio_file_manager.BACKUP_FILE_BASE_PATH', tmp_path / 'backups')
    monkeypatch.setattr('toddler_transducer.web_ui.root.AUDIO_FILE_BASE_PATH', tmp_audio_root)
    (tmp_path / 'backups').mkdir(parents=True, exist_ok=True)
    yield


@pytest.fixture
def vlc_manager() -> dict:
    """Return a plain dict acting as the multiprocessing VLC control dict."""
    return dict(BASE_VLC_STATE)


class FakeValueProxy:
    def __init__(self, initial=None):
        self._value = initial

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, v):
        self._value = v


@pytest.fixture
def rfid_tag_proxy():
    return FakeValueProxy()


@pytest.fixture
def sample_metadata() -> dict:
    return {
        "abc-123": {
            "file_name": "abc-123.ogg",
            "rfid_id": 1001,
            "track_name": "Test Track 1",
        },
        "def-456": {
            "file_name": "def-456.mp3",
            "rfid_id": 1002,
            "track_name": "Test Track 2",
        },
    }


@pytest.fixture
def mock_vlc_instance(monkeypatch):
    """Provide fully mocked vlc.Instance and vlc.MediaListPlayer objects."""
    import vlc
    mock_instance = MagicMock(spec=vlc.Instance)
    mock_media_list_player = MagicMock(spec=vlc.MediaListPlayer)
    mock_media_player = MagicMock()
    mock_media = MagicMock()

    mock_media.get_mrl.return_value = "/fake/path/abc-123.ogg"
    mock_media_player.get_media.return_value = mock_media
    mock_media_player.is_playing.return_value = 1
    mock_media_player.get_length.return_value = 120000
    mock_media_player.get_time.return_value = 30000
    mock_media_list_player.get_media_player.return_value = mock_media_player
    mock_instance.media_new.return_value = mock_media
    mock_instance.media_list_new.return_value = MagicMock()

    monkeypatch.setattr('toddler_transducer.audio.vlc.Instance', lambda *a, **kw: mock_instance)
    return mock_instance, mock_media_list_player, mock_media_player, mock_media


@pytest.fixture
def flask_app(rfid_tag_proxy, vlc_manager):
    """Create a fresh Flask test app per test with routes registered."""
    from pathlib import Path
    from flask import Flask
    templates = str(Path(__file__).parents[1] / 'src' / 'toddler_transducer' / 'web_ui' / 'templates')
    static = str(Path(__file__).parents[1] / 'src' / 'toddler_transducer' / 'web_ui' / 'static')
    app = Flask(__name__, template_folder=templates, static_folder=static)
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret'
    from toddler_transducer.web_ui.root import add_root_routes
    with app.app_context():
        add_root_routes(app, rfid_tag_proxy, vlc_manager)
    yield app


@pytest.fixture
def client(flask_app):
    """Flask test client for HTTP route testing."""
    with flask_app.test_client() as c:
        yield c
