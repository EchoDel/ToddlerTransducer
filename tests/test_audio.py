import json
import time
from pathlib import Path
from unittest.mock import MagicMock, call

import pytest

from toddler_transducer.audio import (
    load_saved_volume,
    save_volume,
    load_saved_puck_lockout,
    save_puck_lockout,
    seconds_to_mmss,
    load_track,
    play_vlc,
    pause_vlc,
    stop_vlc,
    toggle_loop_vlc,
    get_playing_track,
    is_playing,
    get_track_length,
    get_track_time,
    launch_vlc_threaded,
)


class TestVolumePersistence:
    def test_load_saved_volume_default(self):
        assert load_saved_volume() == 50

    def test_save_and_load_volume(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        vol_path = tmp_path / 'persistent_settings.json'
        monkeypatch.setattr('toddler_transducer.audio.VOLUME_FILE_PATH', vol_path)
        save_volume(75)
        assert load_saved_volume() == 75

    def test_save_volume_clamps_above_100(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        vol_path = tmp_path / 'persistent_settings.json'
        monkeypatch.setattr('toddler_transducer.audio.VOLUME_FILE_PATH', vol_path)
        save_volume(999)
        data = json.loads(vol_path.read_text())
        assert data['volume'] == 100

    def test_save_volume_clamps_below_0(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        vol_path = tmp_path / 'persistent_settings.json'
        monkeypatch.setattr('toddler_transducer.audio.VOLUME_FILE_PATH', vol_path)
        save_volume(-10)
        data = json.loads(vol_path.read_text())
        assert data['volume'] == 0

    def test_load_corrupted_volume_returns_default(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        vol_path = tmp_path / 'persistent_settings.json'
        vol_path.write_text("not-json")
        monkeypatch.setattr('toddler_transducer.audio.VOLUME_FILE_PATH', vol_path)
        assert load_saved_volume() == 50

    def test_save_volume_preserves_existing_keys(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        vol_path = tmp_path / 'persistent_settings.json'
        vol_path.write_text(json.dumps({'puck_lockout': True, 'volume': 30}))
        monkeypatch.setattr('toddler_transducer.audio.VOLUME_FILE_PATH', vol_path)
        save_volume(80)
        data = json.loads(vol_path.read_text())
        assert data['volume'] == 80
        assert data['puck_lockout'] is True


class TestPuckLockoutPersistence:
    def test_load_puck_lockout_default(self):
        assert load_saved_puck_lockout() is False

    def test_save_and_load_puck_lockout(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        vol_path = tmp_path / 'persistent_settings.json'
        monkeypatch.setattr('toddler_transducer.audio.VOLUME_FILE_PATH', vol_path)
        save_puck_lockout(True)
        assert load_saved_puck_lockout() is True

    def test_save_puck_lockout_preserves_volume(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        vol_path = tmp_path / 'persistent_settings.json'
        vol_path.write_text(json.dumps({'volume': 42}))
        monkeypatch.setattr('toddler_transducer.audio.VOLUME_FILE_PATH', vol_path)
        save_puck_lockout(True)
        data = json.loads(vol_path.read_text())
        assert data['puck_lockout'] is True
        assert data['volume'] == 42


class TestSecondsToMmss:
    def test_zero(self):
        assert seconds_to_mmss(0) == '00:00'

    def test_exactly_one_minute(self):
        assert seconds_to_mmss(60) == '01:00'

    def test_minutes_and_seconds(self):
        assert seconds_to_mmss(125) == '02:05'

    def test_floating_point(self):
        assert seconds_to_mmss(90.7) == '01:30'


class TestLoadTrack:
    def test_load_by_rfid_tag(self, mock_vlc_instance, tmp_audio_root: Path):
        mock_instance, mock_mlp, mock_mp, mock_media = mock_vlc_instance
        load_track(mock_instance, mock_mlp, looping=False, rfid_tag=1001)
        mock_mlp.stop.assert_called_once()
        mock_instance.media_new.assert_called_once_with(tmp_audio_root / 'abc-123.ogg')

    def test_load_by_track_name(self, mock_vlc_instance, tmp_audio_root: Path):
        mock_instance, mock_mlp, mock_mp, mock_media = mock_vlc_instance
        load_track(mock_instance, mock_mlp, looping=False, track_name='def-456.mp3')
        mock_instance.media_new.assert_called_once_with(tmp_audio_root / 'def-456.mp3')

    def test_load_with_looping_sets_playback_mode(self, mock_vlc_instance):
        mock_instance, mock_mlp, mock_mp, mock_media = mock_vlc_instance
        load_track(mock_instance, mock_mlp, looping=True, track_name='def-456.mp3')
        mock_mlp.set_playback_mode.assert_called_once_with(1)

    def test_load_without_looping_does_not_set_playback_mode(self, mock_vlc_instance):
        mock_instance, mock_mlp, mock_mp, mock_media = mock_vlc_instance
        load_track(mock_instance, mock_mlp, looping=False, track_name='def-456.mp3')
        mock_mlp.set_playback_mode.assert_not_called()

    def test_load_invalid_rfid_does_not_create_media(self, mock_vlc_instance):
        mock_instance, mock_mlp, mock_mp, mock_media = mock_vlc_instance
        load_track(mock_instance, mock_mlp, looping=False, rfid_tag=9999)
        mock_instance.media_new.assert_not_called()

    def test_load_raises_without_args(self, mock_vlc_instance):
        mock_instance, mock_mlp, mock_mp, mock_media = mock_vlc_instance
        with pytest.raises(TypeError, match='Must provide either rfid_tag or track_name'):
            load_track(mock_instance, mock_mlp)


class TestVlcControlFunctions:
    def test_play_vlc(self, mock_vlc_instance):
        _, mock_mlp, _, _ = mock_vlc_instance
        play_vlc(mock_mlp)
        mock_mlp.play.assert_called_once()

    def test_pause_vlc(self, mock_vlc_instance):
        _, mock_mlp, _, _ = mock_vlc_instance
        pause_vlc(mock_mlp)
        mock_mlp.pause.assert_called_once()

    def test_stop_vlc(self, mock_vlc_instance):
        _, mock_mlp, _, _ = mock_vlc_instance
        stop_vlc(mock_mlp)
        mock_mlp.stop.assert_called_once()

    def test_toggle_loop_on(self, mock_vlc_instance):
        _, mock_mlp, _, _ = mock_vlc_instance
        result = toggle_loop_vlc(mock_mlp, False)
        mock_mlp.set_playback_mode.assert_called_once_with(1)
        assert result is True

    def test_toggle_loop_off(self, mock_vlc_instance):
        _, mock_mlp, _, _ = mock_vlc_instance
        result = toggle_loop_vlc(mock_mlp, True)
        mock_mlp.set_playback_mode.assert_called_once_with(0)
        assert result is False


class TestVlcQueries:
    def test_get_playing_track(self, mock_vlc_instance):
        _, mock_mlp, mock_mp, mock_media = mock_vlc_instance
        mock_media.get_mrl.return_value = "file:///audio/abc-123.ogg"
        result = get_playing_track(mock_mlp)
        assert result == 'abc-123'

    def test_get_playing_track_no_media(self, mock_vlc_instance):
        _, mock_mlp, mock_mp, _ = mock_vlc_instance
        mock_mp.get_media.return_value = None
        result = get_playing_track(mock_mlp)
        assert result is None

    def test_is_playing(self, mock_vlc_instance):
        _, mock_mlp, mock_mp, _ = mock_vlc_instance
        mock_mp.is_playing.return_value = 1
        assert is_playing(mock_mlp) is True

    def test_is_not_playing(self, mock_vlc_instance):
        _, mock_mlp, mock_mp, _ = mock_vlc_instance
        mock_mp.is_playing.return_value = 0
        assert is_playing(mock_mlp) is False

    def test_get_track_length(self, mock_vlc_instance):
        _, mock_mlp, mock_mp, _ = mock_vlc_instance
        mock_mp.get_length.return_value = 180000
        assert get_track_length(mock_mlp) == 180.0

    def test_get_track_time(self, mock_vlc_instance):
        _, mock_mlp, mock_mp, _ = mock_vlc_instance
        mock_mp.get_time.return_value = 45000
        assert get_track_time(mock_mlp) == 45.0


class TestLaunchVlcThreaded:
    def test_processes_play_rfid_id(self, vlc_manager, monkeypatch):
        monkeypatch.setattr('toddler_transducer.audio.time.sleep', lambda _: None)
        vlc_manager['play_rfid_id'] = 1001

        import threading
        t = threading.Thread(target=launch_vlc_threaded, args=(vlc_manager,), daemon=True)
        t.start()
        t.join(timeout=0.5)

        assert vlc_manager['play_rfid_id'] is False

    def test_processes_play_track_name(self, vlc_manager, monkeypatch):
        monkeypatch.setattr('toddler_transducer.audio.time.sleep', lambda _: None)
        vlc_manager['play_track_name'] = 'def-456.mp3'

        import threading
        t = threading.Thread(target=launch_vlc_threaded, args=(vlc_manager,), daemon=True)
        t.start()
        t.join(timeout=0.5)

        assert vlc_manager['play_track_name'] is False

    def test_processes_do_stop(self, vlc_manager, monkeypatch):
        monkeypatch.setattr('toddler_transducer.audio.time.sleep', lambda _: None)
        vlc_manager['do_stop'] = True

        import threading
        t = threading.Thread(target=launch_vlc_threaded, args=(vlc_manager,), daemon=True)
        t.start()
        t.join(timeout=0.5)

        assert vlc_manager['do_stop'] is False

    def test_processes_toggle_looping(self, vlc_manager, monkeypatch):
        monkeypatch.setattr('toddler_transducer.audio.time.sleep', lambda _: None)
        vlc_manager['toggle_looping'] = True

        import threading
        t = threading.Thread(target=launch_vlc_threaded, args=(vlc_manager,), daemon=True)
        t.start()
        t.join(timeout=0.5)

        assert vlc_manager['toggle_looping'] is False
