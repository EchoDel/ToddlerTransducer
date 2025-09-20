from typing import Optional

from pygame import mixer
from pathlib import Path

from toddler_transducer.config import AUDIO_FILE_BASE_PATH

# Starting the mixer
mixer.init()


mixer.fadeout(3)


def load_track(rfid_tag: Optional[str], track_name: Optional[str]):
    if rfid_tag is not None:
        audio_path: Path = ''
    elif track_name is not None:
        audio_path: Path = AUDIO_FILE_BASE_PATH / track_name
    else:
        raise TypeError('Must provide either rfid_tag or track_name')
    mixer.music.load(audio_path)
