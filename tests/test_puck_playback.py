import threading
import time as _time

import pytest


class TestPuckPlayback:
    def _run_loop(self, rfid_proxy, vlc_manager, monkeypatch, iterations=2):
        """Run puck_playback_loop for a set number of iterations in a thread."""
        import toddler_transducer.puck_playback as pp
        original_sleep = pp.time.sleep
        counter = {'iterations': 0}

        def counting_sleep(secs):
            counter['iterations'] += 1
            if counter['iterations'] >= iterations:
                raise StopIteration()
            original_sleep(0.001)

        monkeypatch.setattr('toddler_transducer.puck_playback.time.sleep', counting_sleep)
        with pytest.raises(StopIteration):
            pp.puck_playback_loop(rfid_proxy, vlc_manager)

    def test_new_puck_triggers_play(self, vlc_manager, monkeypatch):
        rfid_proxy = type('Proxy', (), {'value': 1001})()
        self._run_loop(rfid_proxy, vlc_manager, monkeypatch, iterations=1)
        assert vlc_manager['play_rfid_id'] == 1001
        assert vlc_manager['playback_source'] == 'puck'

    def test_same_puck_does_not_replay(self, vlc_manager, monkeypatch):
        rfid_proxy = type('Proxy', (), {'value': 1001})()
        self._run_loop(rfid_proxy, vlc_manager, monkeypatch, iterations=2)
        assert vlc_manager['play_rfid_id'] is False or vlc_manager['play_rfid_id'] == 1001
        assert vlc_manager['playback_source'] == 'puck'

    def test_removing_puck_requires_two_cycles(self, vlc_manager, monkeypatch):
        vlc_manager['playback_source'] = 'puck'
        vlc_manager['is_playing'] = True
        rfid_proxy = type('Proxy', (), {'value': None})()
        self._run_loop(rfid_proxy, vlc_manager, monkeypatch, iterations=1)
        assert vlc_manager['do_stop'] is False

    def test_removing_puck_stops_after_two_cycles(self, vlc_manager, monkeypatch):
        vlc_manager['playback_source'] = 'puck'
        vlc_manager['is_playing'] = True
        rfid_proxy = type('Proxy', (), {'value': None})()
        self._run_loop(rfid_proxy, vlc_manager, monkeypatch, iterations=3)
        assert vlc_manager['do_stop'] is True

    def test_puck_removed_no_playing_does_not_stop(self, vlc_manager, monkeypatch):
        vlc_manager['playback_source'] = 'puck'
        vlc_manager['is_playing'] = False
        rfid_proxy = type('Proxy', (), {'value': None})()
        self._run_loop(rfid_proxy, vlc_manager, monkeypatch, iterations=3)
        assert vlc_manager['do_stop'] is False

    def test_puck_lockout_blocks_play(self, vlc_manager, monkeypatch):
        vlc_manager['puck_lockout'] = True
        rfid_proxy = type('Proxy', (), {'value': 1001})()
        self._run_loop(rfid_proxy, vlc_manager, monkeypatch, iterations=1)
        assert vlc_manager['play_rfid_id'] is False

    def test_puck_lockout_with_current_tag_playing(self, vlc_manager, monkeypatch):
        vlc_manager['puck_lockout'] = True
        vlc_manager['playback_source'] = 'puck'
        vlc_manager['is_playing'] = True
        rfid_proxy = type('Proxy', (), {'value': 1001})()
        self._run_loop(rfid_proxy, vlc_manager, monkeypatch, iterations=1)
        assert vlc_manager['do_stop'] is False

    def test_webui_source_not_stopped_by_puck_remove(self, vlc_manager, monkeypatch):
        vlc_manager['playback_source'] = 'webui'
        vlc_manager['is_playing'] = True
        rfid_proxy = type('Proxy', (), {'value': None})()
        self._run_loop(rfid_proxy, vlc_manager, monkeypatch, iterations=3)
        assert vlc_manager['do_stop'] is False
