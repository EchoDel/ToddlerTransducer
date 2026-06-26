import io
import logging
from multiprocessing.managers import DictProxy
from pathlib import Path

import pytest
from werkzeug.datastructures import FileStorage


class TestWebRoutes:
    def test_home_page_returns_200(self, client):
        resp = client.get('/')
        assert resp.status_code == 200

    def test_home_page_contains_track_names(self, client):
        resp = client.get('/')
        assert b'Test Track 1' in resp.data or b'Load Track' in resp.data

    def test_play_track_post(self, client, vlc_manager):
        resp = client.post('/play_track', data={'AudioTrackName': 'Test Track 1'},
                           headers={'Referer': '/'})
        assert resp.status_code == 302
        assert vlc_manager['playback_source'] == 'webui'
        assert vlc_manager['play_track_name'] == 'abc-123.ogg'

    def test_pause_post(self, client, vlc_manager):
        resp = client.post('/pause', headers={'Referer': '/'})
        assert resp.status_code == 302
        assert vlc_manager['do_pause'] is True

    def test_upload_track_needs_file_and_session(self, client):
        resp = client.post('/upload_track', headers={'Referer': '/'})
        assert resp.status_code == 302


class TestApiRoutes:
    def test_api_seek(self, client, vlc_manager):
        resp = client.post('/api/seek', json={'position': 30.0})
        assert resp.status_code == 200
        assert resp.json == {'ok': True}
        assert vlc_manager['seek_position'] == 30.0

    def test_api_volume_set(self, client, vlc_manager):
        resp = client.post('/api/volume', json={'volume': 80})
        assert resp.status_code == 200
        assert vlc_manager['volume'] == 80

    def test_api_volume_clamps(self, client, vlc_manager):
        client.post('/api/volume', json={'volume': 200})
        assert vlc_manager['volume'] == 100

    def test_api_puck_lockout_get(self, client):
        resp = client.get('/api/puck_lockout')
        assert resp.status_code == 200
        assert resp.json == {'puck_lockout': False}

    def test_api_puck_lockout_set(self, client, vlc_manager):
        resp = client.post('/api/puck_lockout', json={'puck_lockout': True})
        assert resp.status_code == 200
        assert vlc_manager['puck_lockout'] is True

    def test_api_player_state(self, client, vlc_manager):
        resp = client.get('/api/player_state')
        assert resp.status_code == 200
        data = resp.json
        assert 'is_playing' in data
        assert 'is_looping' in data
        assert 'track_name' in data
        assert 'volume' in data

    def test_api_play_track(self, client, vlc_manager):
        resp = client.post('/api/play_track', json={'track_name': 'Test Track 1'})
        assert resp.status_code == 200
        assert vlc_manager['play_track_name'] == 'abc-123.ogg'

    def test_api_play_track_invalid(self, client, vlc_manager):
        resp = client.post('/api/play_track', json={'track_name': 'nonexistent'})
        assert resp.status_code == 200
        assert vlc_manager['play_track_name'] is False

    def test_api_toggle_playback_play(self, client, vlc_manager):
        vlc_manager['is_playing'] = False
        resp = client.post('/api/toggle_playback')
        assert resp.status_code == 200
        assert vlc_manager['do_play'] is True

    def test_api_toggle_playback_pause(self, client, vlc_manager):
        vlc_manager['is_playing'] = True
        resp = client.post('/api/toggle_playback')
        assert resp.status_code == 200
        assert vlc_manager['do_pause'] is True

    def test_api_toggle_loop(self, client, vlc_manager):
        resp = client.post('/api/toggle_loop')
        assert resp.status_code == 200
        assert vlc_manager['toggle_looping'] is True

    def test_api_tracks(self, client):
        resp = client.get('/api/tracks')
        assert resp.status_code == 200
        assert 'tracks' in resp.json

    def test_loop_track_post(self, client, vlc_manager):
        resp = client.post('/loop_track', headers={'Referer': '/'})
        assert resp.status_code == 302
        assert vlc_manager['toggle_looping'] is True


class TestUploadFlow:
    def test_upload_with_session_and_file(self, client, rfid_tag_proxy, tmp_audio_root: Path,
                                           monkeypatch: pytest.MonkeyPatch):
        rfid_tag_proxy.value = 9999
        home_resp = client.get('/')
        assert home_resp.status_code == 200
        data = {
            'TrackFile': FileStorage(stream=io.BytesIO(b'fake audio content'),
                                     filename='my_track.wav',
                                     content_type='audio/wav'),
            'TrackName': 'Uploaded Track',
        }
        resp = client.post('/upload_track', data=data, headers={'Referer': '/'})
        assert resp.status_code == 302
        from toddler_transducer.metadata import load_metadata
        meta = load_metadata()
        track_names = [v['track_name'] for v in meta.values()]
        assert 'Uploaded Track' in track_names
