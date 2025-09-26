import json
from typing import TypedDict

from toddler_transducer.config import METADATA_FILE_PATH


class TrackMetadata(TypedDict):
    file_name: str
    rfid_id: int
    track_name: str


class Metadata(TypedDict):
    metadata: TrackMetadata


def load_metadata() -> Metadata:
    if METADATA_FILE_PATH.exists():
        with open(METADATA_FILE_PATH) as f:
            metadata = json.load(f)
        return metadata
    return {}


def save_metadata(metadata):
    METADATA_FILE_PATH.write_text(json.dumps(metadata))

METADATA = load_metadata()
