"""
Metadata

Module containing the functions for working with the metadata of the audio files.
"""
import json
import time
from typing import TypedDict
from shutil import copy2

from toddler_transducer.config import METADATA_FILE_PATH


class TrackMetadata(TypedDict):
    """The metadata of the audio files."""
    file_name: str
    rfid_id: int
    track_name: str


def load_metadata() -> dict[str, TrackMetadata]:
    """
    Loads the metadata of the audio files.

    Returns:
        (dict[str, TrackMetadata]): The metadata of the audio files.
    """
    if METADATA_FILE_PATH.exists():
        with open(METADATA_FILE_PATH, encoding='UTF-8') as f:
            metadata = json.load(f)
        return metadata
    return {}


def save_metadata(metadata: dict[str, TrackMetadata]):
    """
    Saves the metadata of the audio files backing up the prior version first.

    Args:
        metadata (dict[str, TrackMetadata]): The metadata of the audio files to be saved.
    """
    metadata_backup_name = f'{METADATA_FILE_PATH.name}_{time.strftime("%Y%m%d-%H%M%S")}'
    copy2(METADATA_FILE_PATH, METADATA_FILE_PATH.with_name(metadata_backup_name))
    METADATA_FILE_PATH.write_text(json.dumps(metadata), encoding='UTF-8')


def remove_from_metadata(uuid: str) -> TrackMetadata | None:
    """
    Removes a track from the metadata store by UUID.

    Args:
        uuid (str): The uuid of the audio file to remove.

    Returns:
        TrackMetadata | None: The removed metadata entry, or None if not found.
    """
    metadata = load_metadata()
    entry = metadata.pop(uuid, None)
    if entry is not None:
        save_metadata(metadata)
    return entry


def remove_from_metadata_by_track_name(track_name: str) -> dict | None:
    """
    Removes a track from the metadata store by track name.

    Args:
        track_name (str): The display name of the track to remove.

    Returns:
        dict | None: The removed metadata entry, or None if not found.
    """
    metadata = load_metadata()
    for uuid, entry in list(metadata.items()):
        if entry.get('track_name') == track_name:
            del metadata[uuid]
            save_metadata(metadata)
            return entry | {'uuid': uuid}
    return None


def append_to_metadata(uuid: str, file_name: str, puck_id: int, track_name: str):
    """
    Appends a new audio files metadata to the metadata store.

    Args:
        uuid (str): The uuid of the audio file.
        file_name (str): The name of the audio file.
        puck_id (int): The id of the puck.
        track_name (str): The name of the track to show in the web ui.
    """
    metadata = load_metadata()
    metadata[uuid] = {'file_name': file_name,
                      'rfid_id': puck_id,
                      'track_name': track_name}
    save_metadata(metadata)


METADATA = load_metadata()
