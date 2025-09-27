from toddler_transducer.audio import load_track, is_playing, stop_vlc
from toddler_transducer.metadata import load_metadata
from toddler_transducer.rfid import get_rfid_id


def main():
    current_tag_id = None
    while True:
        rfid_tag = get_rfid_id()
        if rfid_tag == current_tag_id:
            continue

        if rfid_tag is not None:
            load_track(rfid_tag=rfid_tag)
        else:
            if is_playing():
                stop_vlc()
