from .config import AUDIO_FILE_BASE_PATH

def get_current_files():
    return {x.name: x for x in AUDIO_FILE_BASE_PATH.glob('*')}
