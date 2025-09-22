"""
Audio

Contains all the code to load, play, stop the audio to play

This uses the py vlc interface, api reference, https://www.olivieraubert.net/vlc/python-ctypes/doc/.

"""

from typing import Optional

import vlc
from pathlib import Path

from .config import AUDIO_FILE_BASE_PATH


# Starting the vlc instance
VLC_MEDIA_PLAYER= vlc.MediaPlayer()


def load_track(rfid_tag: Optional[str] = None, track_name: Optional[str] = None):
    if rfid_tag is not None:
        audio_path: Path = ''
    elif track_name is not None:
        audio_path: Path = AUDIO_FILE_BASE_PATH / track_name
    else:
        raise TypeError('Must provide either rfid_tag or track_name')
    print(audio_path)
    VLC_MEDIA_PLAYER.set_mrl(audio_path)
    VLC_MEDIA_PLAYER.play()
