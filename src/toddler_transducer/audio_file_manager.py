from .config import AUDIO_FILE_BASE_PATH
from .metadata import load_metadata


def get_current_files():
    metadata = load_metadata()
    return {x['track_name']: x['file_name'] for x in metadata.values()}
