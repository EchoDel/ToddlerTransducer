"""
Audio

Contains all the code to load, play, stop the audio to play

This uses the py vlc interface, api reference, https://www.olivieraubert.net/vlc/python-ctypes/doc/.

"""
import logging
import time
from typing import Optional

import vlc
from pathlib import Path

from .config import AUDIO_FILE_BASE_PATH
from .metadata import load_metadata, TrackMetadata

# Starting the vlc instance
VLC_MEDIA_INSTANCE = vlc.Instance("--aout=alsa")
VLC_MEDIA_LIST_PLAYER = VLC_MEDIA_INSTANCE.media_list_player_new()

LOOPING = False


def load_track(rfid_tag: Optional[int] = None, track_name: Optional[str] = None):
    if rfid_tag is not None:
        metadata = load_metadata()
        track_to_play = [value for key, value in metadata.items() if value['rfid_id'] == rfid_tag]
        if len(track_to_play) > 0:
            audio_path: Path = AUDIO_FILE_BASE_PATH / track_to_play[0]['file_name']
        else:
            logging.warning(f"No track found for {rfid_tag}")
            return
    elif track_name is not None:
        audio_path: Path = AUDIO_FILE_BASE_PATH / track_name
    else:
        raise TypeError('Must provide either rfid_tag or track_name')
    print(audio_path)
    VLC_MEDIA_LIST_PLAYER.stop()
    media = VLC_MEDIA_INSTANCE.media_new(audio_path)
    media_list = VLC_MEDIA_INSTANCE.media_list_new()
    media_list.add_media(media)
    VLC_MEDIA_LIST_PLAYER.set_media_list(media_list)
    VLC_MEDIA_LIST_PLAYER.play()
    VLC_MEDIA_LIST_PLAYER.get_media_player().audio_set_volume(100)
    if LOOPING:
        VLC_MEDIA_LIST_PLAYER.set_playback_mode(int(LOOPING))


def play_vlc():
    """
    Calls the VLC service to play audio.
    """
    VLC_MEDIA_LIST_PLAYER.play()


def pause_vlc():
    """
    Calls the VLC service to pause audio.
    """
    VLC_MEDIA_LIST_PLAYER.pause()


def stop_vlc():
    """
    Calls the VLC service to stop audio.
    """
    VLC_MEDIA_LIST_PLAYER.stop()


def toggle_loop_vlc():
    """
    Calls the VLC service to loop the current audio.
    """
    global LOOPING
    VLC_MEDIA_LIST_PLAYER.set_playback_mode(int(not LOOPING))
    LOOPING = not LOOPING


def get_looping() -> bool:
    """
    Returns whether the VLC service is currently looping.

    Returns:
        (bool): True if looping, False if not.
    """
    return LOOPING


def get_playing_track() -> TrackMetadata:
    """
    Returns the metadata of the playing track.

    Returns:
        (TrackMetadata): The metadata of the playing track.
    """
    media = VLC_MEDIA_LIST_PLAYER.get_media_player().get_media()
    if media is None:
        return None
    mrl = Path(media.get_mrl())
    uuid = mrl.stem
    metadata = load_metadata()
    return metadata[uuid]


def is_playing() -> bool:
    """
    Returns whether the VLC service is currently playing audio.

    Returns:
        (bool): True if playing, False if not.
    """
    return VLC_MEDIA_LIST_PLAYER.get_media_player().is_playing() == 1


def seconds_to_mmss(seconds: float) -> str:
    """
    Converts seconds to pretty print %M:%S.

    Args:
        seconds (float): seconds to convert.

    Returns:
        (str): The time converted to %M:%S
    """
    return time.strftime('%M:%S', time.gmtime(seconds))


def get_track_length() -> str:
    """
    Returns the length of the audio track in the format %M:%S.

    Returns:
        (str): The length of the audio track in the format %M:%S.
    """
    track_length = seconds_to_mmss(VLC_MEDIA_LIST_PLAYER.get_media_player().get_length() / 1000)
    return track_length


def get_track_time() -> str:
    """
    Returns the time the current track has been playing in the format %M:%S.

    Returns:
        (str): The time through the audio track in the format %M:%S.
    """
    play_time = seconds_to_mmss(VLC_MEDIA_LIST_PLAYER.get_media_player().get_time() / 1000)
    return play_time
