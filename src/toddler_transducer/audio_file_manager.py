"""
Audio File Manager

Module which manages the audio files for the tool.
"""
import itertools
import json
from datetime import datetime
from pathlib import Path
from shutil import make_archive

from .config import AUDIO_FILE_BASE_PATH, BACKUP_FILE_BASE_PATH
from .metadata import load_metadata


def get_current_files():
    metadata = load_metadata()
    return {x['track_name']: x['file_name'] for x in metadata.values()}


def load_backup_metadata() -> dict[datetime, str]:
    backup_list_file = BACKUP_FILE_BASE_PATH / 'backup_list.json'
    if backup_list_file.exists():
        with open(backup_list_file, 'r', encoding='UTF-8') as f:
            backup_list = json.load(f)
    else:
        backup_list = []
    return backup_list


def save_backup_metadata(backup_list: dict[datetime, str]):
    backup_list_file = BACKUP_FILE_BASE_PATH / 'backup_list.json'
    with open(backup_list_file, 'w', encoding='UTF-8') as f:
        json.dump(backup_list, f)


def delete_old_backups(backups_to_delete: dict[datetime, str],
                       prior_backups: dict[datetime, str]) -> dict[datetime, str]:
    # Delete the old backups
    for backup_key, backup_path in backups_to_delete.items():
        prior_backups[backup_key] = None
        Path(backup_path).unlink()
    return prior_backups


def get_sorted_backup_item(location: int):
    prior_backups = load_backup_metadata()
    sorted_dict = dict(sorted(prior_backups.items()))
    # https://stackoverflow.com/questions/16976096/take-the-first-x-elements-of-a-dictionary-on-python
    return dict(itertools.islice(sorted_dict.items(), location))


def backup_audio_files():
    prior_backups = load_backup_metadata()
    backup_time = datetime.now().strftime("%Y%m%d%H%M%S")
    backup_file = BACKUP_FILE_BASE_PATH / f'backup_{backup_time}.zip'
    make_archive(AUDIO_FILE_BASE_PATH, 'zip', backup_file)

    # Delete the old backups
    todays_backups = {key: value for key, value in prior_backups.items() if key.date() == datetime.now().date()}
    if len(todays_backups) > 1:
        prior_backups = delete_old_backups(todays_backups, prior_backups)

    # Save the backup
    prior_backups[backup_time] = backup_file

    # Delete the old backups
    if len(prior_backups) > 7:
        sorted_dict = dict(sorted(prior_backups.items()))
        items_to_remove = dict(itertools.islice(sorted_dict.items(), len(prior_backups) - 7))
        prior_backups = delete_old_backups(items_to_remove, prior_backups)

    save_backup_metadata(prior_backups)
