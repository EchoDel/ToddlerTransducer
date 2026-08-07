import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.skipif(
    not sys.platform.startswith('linux'),
    reason='VLC audio output tests require Linux (ideally Raspberry Pi)',
)
class TestVlcAudioOutput:
    """Tests that verify VLC can initialise audio output using a null/dummy
    audio output module.

    On a real Raspberry Pi these tests confirm that ``--aout=alsa`` works with
    system audio.  On CI or non-Pi Linux they use VLC's built-in dummy output
    (``--aout=adummy``) so no hardware audio device is needed.
    """

    @pytest.fixture
    def dummy_vlc_instance(self):
        import vlc
        inst = vlc.Instance('--aout=adummy', '--quiet')
        yield inst

    def test_vlc_can_instantiate(self, dummy_vlc_instance):
        assert dummy_vlc_instance is not None

    def test_media_list_player_creation(self, dummy_vlc_instance):
        mlp = dummy_vlc_instance.media_list_player_new()
        assert mlp is not None

    def test_media_player_from_media_list_player(self, dummy_vlc_instance):
        mlp = dummy_vlc_instance.media_list_player_new()
        mp = mlp.get_media_player()
        assert mp is not None

    def test_track_load_and_query(self, dummy_vlc_instance, tmp_audio_root: Path):
        mlp = dummy_vlc_instance.media_list_player_new()
        track = tmp_audio_root / 'abc-123.ogg'
        media = dummy_vlc_instance.media_new(str(track))
        media_list = dummy_vlc_instance.media_list_new()
        media_list.add_media(media)
        mlp.set_media_list(media_list)
        mrl = media.get_mrl()
        assert 'abc-123.ogg' in mrl

    def test_play_stop_cycle(self, dummy_vlc_instance, tmp_audio_root: Path):
        mlp = dummy_vlc_instance.media_list_player_new()
        track = tmp_audio_root / 'abc-123.ogg'
        media = dummy_vlc_instance.media_new(str(track))
        media_list = dummy_vlc_instance.media_list_new()
        media_list.add_media(media)
        mlp.set_media_list(media_list)
        mlp.play()
        import time
        time.sleep(0.5)
        mlp.stop()
        mp = mlp.get_media_player()
        assert not mp.is_playing()

    def test_volume_api_does_not_raise(self, dummy_vlc_instance):
        mlp = dummy_vlc_instance.media_list_player_new()
        mp = mlp.get_media_player()
        mp.audio_set_volume(80)
        vol = mp.audio_get_volume()
        assert isinstance(vol, int)


class TestFullPipeline:
    """Integration tests that verify the full pipeline:
    RFID tag -> puck playback logic -> VLC control dict -> audio loading.
    """

    def test_rfid_puck_to_vlc_control(self, mock_vlc_instance, monkeypatch):
        monkeypatch.setattr('toddler_transducer.puck_playback.time.sleep',
                            lambda _: (_ for _ in ()).throw(StopIteration))
        from toddler_transducer.puck_playback import puck_playback_loop
        from toddler_transducer.audio import load_track

        class FakeProxy:
            value = 1001

        control = {
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

        rfid_proxy = FakeProxy()
        with pytest.raises(StopIteration):
            puck_playback_loop(rfid_proxy, control)
        assert control['play_rfid_id'] == 1001
        assert control['playback_source'] == 'puck'

        mock_instance, mock_mlp, _, _ = mock_vlc_instance
        load_track(mock_instance, mock_mlp, rfid_tag=control['play_rfid_id'])
        mock_instance.media_new.assert_called()

    def test_webui_play_track_updates_vlc_control(self, client, vlc_manager):
        client.post('/api/play_track', json={'track_name': 'Test Track 1'})
        assert vlc_manager['playback_source'] == 'webui'
        assert vlc_manager['play_track_name'] == 'abc-123.ogg'

    def test_volume_persists_across_cycles(self, client, vlc_manager, tmp_path, monkeypatch):
        vol_path = tmp_path / 'persistent_settings.json'
        monkeypatch.setattr('toddler_transducer.audio.VOLUME_FILE_PATH', vol_path)
        monkeypatch.setattr('toddler_transducer.web_ui.root.save_volume',
                            lambda v: vol_path.write_text(json.dumps({'volume': v})))
        client.post('/api/volume', json={'volume': 42})
        data = json.loads(vol_path.read_text())
        assert data['volume'] == 42
