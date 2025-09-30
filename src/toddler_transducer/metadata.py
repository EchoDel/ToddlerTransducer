"""
Metadata

Module containing the functions for working with the metadata of the audio files.
"""
import json
from typing import TypedDict

from toddler_transducer.config import METADATA_FILE_PATH


class TrackMetadata(TypedDict):
    """The metadata of the audio files."""
    file_name: str
    rfid_id: int
    track_name: str


class Metadata(TypedDict):
    """The metadata dict for all the audio files."""
    metadata: TrackMetadata


def load_metadata() -> Metadata:
    """
    Loads the metadata of the audio files.

    Returns:
        (Metadata): The metadata of the audio files.
    """
    if METADATA_FILE_PATH.exists():
        with open(METADATA_FILE_PATH, encoding='UTF-8') as f:
            metadata = json.load(f)
        return metadata
    return {}


def save_metadata(metadata):
    """
    Saves the metadata of the audio files.

    Args:
        metadata (Metadata): The metadata of the audio files to be saved.
    """
    METADATA_FILE_PATH.write_text(json.dumps(metadata), encoding='UTF-8')


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
