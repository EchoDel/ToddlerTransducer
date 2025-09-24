"""
Audio

Contains all the code to load, play, stop the audio to play

This uses the py vlc interface, api reference, https://www.olivieraubert.net/vlc/python-ctypes/doc/.

"""
import time
from typing import Optional

import vlc
from pathlib import Path

from .config import AUDIO_FILE_BASE_PATH
from .metadata import load_metadata

# Starting the vlc instance
# VLC_MEDIA_PLAYER= vlc.MediaPlayer()

VLC_MEDIA_INSTANCE = vlc.Instance()
VLC_MEDIA_LIST_PLAYER = VLC_MEDIA_INSTANCE.media_list_player_new()

LOOPING = False


def load_track(rfid_tag: Optional[str] = None, track_name: Optional[str] = None):
    if rfid_tag is not None:
        audio_path: Path = ''
    elif track_name is not None:
        audio_path: Path = AUDIO_FILE_BASE_PATH / track_name
    else:
        raise TypeError('Must provide either rfid_tag or track_name')
    print(audio_path)
    global VLC_MEDIA_PLAYER
    VLC_MEDIA_LIST_PLAYER.stop()
    media = VLC_MEDIA_INSTANCE.media_new(audio_path)
    media_list = VLC_MEDIA_INSTANCE.media_list_new()
    media_list.add_media(media)
    VLC_MEDIA_LIST_PLAYER.set_media_list(media_list)
    VLC_MEDIA_LIST_PLAYER.play()


def play_vlc():
    VLC_MEDIA_LIST_PLAYER.play()


def pause_vlc():
    VLC_MEDIA_LIST_PLAYER.pause()


def toggle_loop_vlc():
    global LOOPING
    VLC_MEDIA_LIST_PLAYER.set_playback_mode(int(not LOOPING))
    LOOPING = not LOOPING


def get_looping():
    return LOOPING


def get_playing_track():
    media = VLC_MEDIA_LIST_PLAYER.get_media_player().get_media()
    if media is None:
        return None
    mrl = Path(media.get_mrl())
    uuid = mrl.stem
    metadata = load_metadata()
    return metadata[uuid]


def is_playing():
    return VLC_MEDIA_LIST_PLAYER.get_media_player().is_playing() == 1


def seconds_to_mmss(seconds):
    return time.strftime('%M:%S', time.gmtime(seconds))


def get_track_length():
    track_length = seconds_to_mmss(VLC_MEDIA_LIST_PLAYER.get_media_player().get_length() / 1000)
    return track_length


def get_track_time():
    play_time = seconds_to_mmss(VLC_MEDIA_LIST_PLAYER.get_media_player().get_time() / 1000)
    return play_time
