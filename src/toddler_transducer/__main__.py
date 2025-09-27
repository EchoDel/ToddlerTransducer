from toddler_transducer.audio import load_track, is_playing, stop_vlc
from toddler_transducer.metadata import load_metadata
from toddler_transducer.rfid import get_rfid_id


def main():
    current_tag_id = None
    while True:
        id = get_rfid_id()
        if id == current_tag_id:
            continue

        if id is not None:
            metadata = load_metadata()
            track_to_play = [x for x in metadata.items() if x['rfid_id'] == id]
            current_tag_id = id
            if len(track_to_play) > 0:
                load_track(track_to_play['file_name'])
        else:
            if is_playing():
                stop_vlc()
