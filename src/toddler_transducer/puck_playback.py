import time
from multiprocessing.managers import ValueProxy

from toddler_transducer.audio import is_playing, stop_vlc, load_track


def puck_playback_loop(rfid_tag_proxy: ValueProxy):
    current_tag_id = None
    puck_remove_count = 0
    while True:
        rfid_tag = rfid_tag_proxy.value
        if rfid_tag is None:
            if puck_remove_count >= 1:
                if is_playing():
                    stop_vlc()
                    current_tag_id = rfid_tag
            else:
                puck_remove_count += 1
        elif rfid_tag != current_tag_id:
            if rfid_tag is not None:
                load_track(rfid_tag=rfid_tag)
                current_tag_id = rfid_tag
                puck_remove_count = 0
        elif rfid_tag != current_tag_id:
            puck_remove_count = 0
        time.sleep(2)
