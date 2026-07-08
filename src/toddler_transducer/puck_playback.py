"""
Puck Playback

Module containing the code needed to play a song based on the contents of a rfid tag being placed on a reader.
"""
import time
from multiprocessing.managers import ValueProxy, DictProxy


def puck_playback_loop(rfid_tag_proxy: ValueProxy, vlc_playback_manager: DictProxy) -> None:
    """Infinite loop that reads RFID tag and triggers VLC play/stop.

    Uses a 2-cycle debounce before stopping playback on puck removal.

    Args:
        rfid_tag_proxy (ValueProxy): Proxy with a .value attribute holding the current RFID tag id.
        vlc_playback_manager (DictProxy): Shared dict for VLC control and state.
    """
    current_tag_id = None
    puck_remove_count = 0
    while True:
        if vlc_playback_manager.get('puck_lockout', False):
            current_tag_id = None
            puck_remove_count = 0
            time.sleep(2)
            continue
        rfid_tag = rfid_tag_proxy.value
        if rfid_tag is None:
            if vlc_playback_manager['playback_source'] == 'puck':
                if puck_remove_count >= 1:
                    if vlc_playback_manager['is_playing']:
                        vlc_playback_manager['do_stop'] = True
                        current_tag_id = rfid_tag
                else:
                    puck_remove_count += 1
        elif rfid_tag != current_tag_id:
            vlc_playback_manager['play_rfid_id'] = rfid_tag
            vlc_playback_manager['playback_source'] = 'puck'
            current_tag_id = rfid_tag
            puck_remove_count = 0
        else:
            puck_remove_count = 0
        time.sleep(2)
