"""
Audio

Contains all the code to load, play, stop the audio to play

This uses the py vlc interface, api reference, https://www.olivieraubert.net/vlc/python-ctypes/doc/.

"""
import logging
import time
from typing import Optional, TypedDict, Literal
from pathlib import Path

import vlc

from toddler_transducer.config import AUDIO_FILE_BASE_PATH
from toddler_transducer.metadata import load_metadata


def seconds_to_mmss(seconds: float) -> str:
    """
    Converts seconds to pretty print %M:%S.

    Args:
        seconds (float): seconds to convert.

    Returns:
        (str): The time converted to %M:%S
    """
    return time.strftime('%M:%S', time.gmtime(seconds))


class VLCControlDict(TypedDict):
    """Defined what values are expected in the dictionary passed between the threads and the VLC manager."""
    # Inputs to vlc
    play_rfid_id: int
    play_track_name: str
    do_play: bool
    do_stop: bool
    do_pause: bool
    toggle_looping: bool

    # State outputs
    playback_source: Literal['puck', 'webui']
    is_playing: bool
    is_looping: bool
    current_playing_track_uuid: str
    track_length: float
    track_time_through: float


def load_track(vlc_instance: vlc.Instance, vlc_media_list_player: vlc.MediaListPlayer,
               looping: bool = False, rfid_tag: Optional[int] = None, track_name: Optional[str] = None,):
    """
    Loads a track into a vlc instance.

    Args:
        vlc_instance (vlc.Instance): The vlc instance to load the track into.
        vlc_media_list_player (vlc.MediaListPlayer): The vlc media list player to load the track into.
        looping (bool, optional): Whether to loop the vlc instance. Defaults to False.
        rfid_tag (Optional[int], optional): The tag of the rfid tag to use. Defaults to None.
        track_name (Optional[str], optional): The track name to use. Defaults to None.
    """
    if rfid_tag is not None:
        metadata = load_metadata()
        track_to_play = [value for key, value in metadata.items() if value['rfid_id'] == rfid_tag]
        if len(track_to_play) > 0:
            audio_path: Path = AUDIO_FILE_BASE_PATH / track_to_play[0]['file_name']
        else:
            logging.warning("No track found for %s", rfid_tag)
            return
    elif track_name is not None:
        audio_path: Path = AUDIO_FILE_BASE_PATH / track_name
    else:
        raise TypeError('Must provide either rfid_tag or track_name')
    vlc_media_list_player.stop()
    media = vlc_instance.media_new(audio_path)
    media_list = vlc_instance.media_list_new()
    media_list.add_media(media)
    vlc_media_list_player.set_media_list(media_list)
    vlc_media_list_player.play()
    vlc_media_list_player.get_media_player().audio_set_volume(100)
    if looping:
        vlc_media_list_player.set_playback_mode(1)


def play_vlc(vlc_media_list_player: vlc.MediaListPlayer):
    """
    Calls the VLC service to play audio.
    """
    vlc_media_list_player.play()


def pause_vlc(vlc_media_list_player: vlc.MediaListPlayer):
    """
    Calls the VLC service to pause audio.
    """
    vlc_media_list_player.pause()


def stop_vlc(vlc_media_list_player: vlc.MediaListPlayer):
    """
    Calls the VLC service to stop audio.
    """
    vlc_media_list_player.stop()


def toggle_loop_vlc(vlc_media_list_player: vlc.MediaListPlayer, looping: bool):
    """
    Calls the VLC service to loop the current audio.
    """
    vlc_media_list_player.set_playback_mode(int(not looping))
    return not looping


def get_playing_track(vlc_media_list_player: vlc.MediaListPlayer) -> str:
    """
    Returns the metadata of the playing track.

    Returns:
        (str): The uuid of the playing track.
    """
    media = vlc_media_list_player.get_media_player().get_media()
    if media is None:
        return None
    mrl = Path(media.get_mrl())
    uuid = mrl.stem
    return uuid


def is_playing(vlc_media_list_player: vlc.MediaListPlayer) -> bool:
    """
    Returns whether the VLC service is currently playing audio.

    Returns:
        (bool): True if playing, False if not.
    """
    return vlc_media_list_player.get_media_player().is_playing() == 1


def get_track_length(vlc_media_list_player: vlc.MediaListPlayer) -> float:
    """
    Returns the length of the audio track in seconds.

    Returns:
        (float): The length of the audio track in seconds.
    """
    track_length = vlc_media_list_player.get_media_player().get_length() / 1000
    return track_length


def get_track_time(vlc_media_list_player: vlc.MediaListPlayer) -> float:
    """
    Returns the time the current track has been playing in seconds.

    Returns:
        (str): The time through the audio track in seconds.
    """
    play_time = vlc_media_list_player.get_media_player().get_time() / 1000
    return play_time


def launch_vlc_threaded(vlc_playback_manager: VLCControlDict):
    """
    Launch the vlc instance to be used with the vlc control dict

    Args:
        vlc_playback_manager (VLCControlDict): VLCControlDict instance:
    """
    # Starting the vlc instance
    vlc_instance = vlc.Instance("--aout=alsa")
    vlc_media_list_player = vlc_instance.media_list_player_new()

    while True:
        if vlc_playback_manager['play_rfid_id']:
            load_track(vlc_instance, vlc_media_list_player, vlc_playback_manager['is_looping'],
                       rfid_tag=vlc_playback_manager['play_rfid_id'])
            vlc_playback_manager['play_rfid_id'] = False

        if vlc_playback_manager['play_track_name']:
            load_track(vlc_instance, vlc_media_list_player, vlc_playback_manager['is_looping'],
                       track_name=vlc_playback_manager['play_track_name'])
            vlc_playback_manager['play_track_name'] = False

        if vlc_playback_manager['do_play']:
            play_vlc(vlc_media_list_player)
            vlc_playback_manager['do_play'] = False

        if vlc_playback_manager['do_pause']:
            pause_vlc(vlc_media_list_player)
            vlc_playback_manager['do_pause'] = False

        if vlc_playback_manager['do_stop']:
            stop_vlc(vlc_media_list_player)
            vlc_playback_manager['do_stop'] = False

        if vlc_playback_manager['toggle_looping']:
            vlc_playback_manager['is_looping'] = toggle_loop_vlc(vlc_media_list_player,
                                                                 vlc_playback_manager['is_looping'])
            vlc_playback_manager['toggle_looping'] = False

        vlc_playback_manager['is_playing'] = is_playing(vlc_media_list_player)
        vlc_playback_manager['current_playing_track_uuid'] = get_playing_track(vlc_media_list_player)
        vlc_playback_manager['track_length'] = get_track_length(vlc_media_list_player)
        vlc_playback_manager['track_time_through'] = get_track_time(vlc_media_list_player)

        time.sleep(1)
