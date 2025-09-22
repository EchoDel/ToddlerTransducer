import json

from toddler_transducer.config import METADATA_FILE_PATH


def load_metadata():
    if METADATA_FILE_PATH.exists():
        with open(METADATA_FILE_PATH) as f:
            metadata = json.load(f)
        return metadata
    return {}


def save_metadata(metadata):
    METADATA_FILE_PATH.write_text(json.dumps(metadata))

METADATA = load_metadata()
