"""
Audio File Manager

Module which manages the audio files for the tool.
"""
import itertools
import json
from datetime import datetime
from pathlib import Path
from shutil import make_archive

from toddler_transducer.config import AUDIO_FILE_BASE_PATH, BACKUP_FILE_BASE_PATH
from toddler_transducer.metadata import load_metadata


def get_current_files() -> dict[str, Path]:
    """
    Get current audio file paths.

    Returns:
        dict[str, Path]: The current audio file paths.
    """
    metadata = load_metadata()
    return {x['track_name']: x['file_name'] for x in metadata.values()}


def load_backup_metadata() -> dict[datetime, str]:
    """
    Load the backup metadata from disk.

    Returns:
        dict[datetime, str]: The backup metadata.
    """
    backup_list_file = BACKUP_FILE_BASE_PATH / 'backup_list.json'
    if backup_list_file.exists():
        with open(backup_list_file, 'r', encoding='UTF-8') as f:
            backup_list = json.load(f)
    else:
        backup_list = {}

    backup_list = {datetime.strptime(key, '%Y%m%d%H%M%S'): value for key, value in backup_list.items()}
    return backup_list


def save_backup_metadata(backup_list: dict[datetime, str]):
    """
    Save the backup metadata to disk.

    Args:
        backup_list (dict[datetime, str]): The backup metadata.:
    """
    backup_list_file = BACKUP_FILE_BASE_PATH / 'backup_list.json'
    backup_list = {key.strftime('%Y%m%d%H%M%S'): value for key, value in backup_list.items()}

    with open(backup_list_file, 'w', encoding='UTF-8') as f:
        json.dump(backup_list, f)


def delete_old_backups(backups_to_delete: dict[datetime, str],
                       prior_backups: dict[datetime, str]) -> dict[datetime, str]:
    """
    Delete old backups.

    Args:
        backups_to_delete dict[datetime, str]: The backups to delete.
        prior_backups (dict[datetime, str]): All dict of all backups.

    Returns:
        dict[datetime, str]: The new backup metadat with the old backups deleted.
    """
    # Delete the old backups
    for backup_key, backup_path in backups_to_delete.items():
        prior_backups[backup_key] = None
        Path(backup_path).unlink()
    return prior_backups


def get_sorted_backup_item(location: int) ->  dict[datetime, str]:
    """
    Gets the single item from the backup list.

    Args:
        location int: The location of the item.

    Returns:
         dict[datetime, str]: The single value from the backup dict.
    """
    prior_backups = load_backup_metadata()
    if location < 0:
        sorted_dict = dict(sorted(prior_backups.items(), reverse=True))
        location = -location
    else:
        sorted_dict = dict(sorted(prior_backups.items()))
    # https://stackoverflow.com/questions/16976096/take-the-first-x-elements-of-a-dictionary-on-python
    return dict(itertools.islice(sorted_dict.items(), location))


def backup_audio_files():
    """
    Runs the full backup process creating a zip of the audio files folder and a metadata record for the backup.
    """
    prior_backups = load_backup_metadata()
    backup_time = datetime.now()
    backup_file = BACKUP_FILE_BASE_PATH / f'backup_{backup_time.strftime("%Y%m%d%H%M%S")}'
    make_archive(backup_file, 'zip', AUDIO_FILE_BASE_PATH)

    # Delete the old backups
    todays_backups = {key: value for key, value in prior_backups.items() if key.date() == datetime.now().date()}
    if len(todays_backups) > 1:
        prior_backups = delete_old_backups(todays_backups, prior_backups)

    # Save the backup
    prior_backups[backup_time] = str(backup_file.with_suffix('.zip'))

    # Delete the old backups
    if len(prior_backups) > 7:
        sorted_dict = dict(sorted(prior_backups.items()))
        items_to_remove = dict(itertools.islice(sorted_dict.items(), len(prior_backups) - 7))
        prior_backups = delete_old_backups(items_to_remove, prior_backups)

    save_backup_metadata(prior_backups)
