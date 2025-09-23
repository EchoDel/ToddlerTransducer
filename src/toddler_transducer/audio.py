"""
Audio

Contains all the code to load, play, stop the audio to play

This uses the py vlc interface, api reference, https://www.olivieraubert.net/vlc/python-ctypes/doc/.

"""

from typing import Optional

import vlc
from pathlib import Path

from .audio_file_manager import get_current_files
from .config import AUDIO_FILE_BASE_PATH
from .metadata import load_metadata

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

def get_playing_track():
    media = VLC_MEDIA_PLAYER.get_media()
    if media is None:
        return None
    mrl = Path(media.get_mrl())
    uuid = mrl.stem
    metadata = load_metadata()
    return metadata[uuid]


def is_playing():
    return VLC_MEDIA_PLAYER.is_playing() == 1
