"""
Config

Module containing the config for the application
"""
from pathlib import Path

AUDIO_FILE_BASE_PATH = Path('./audio_files')
METADATA_FILE_PATH = AUDIO_FILE_BASE_PATH / 'metadata'
BACKUP_FILE_BASE_PATH = Path('./backups')

# GPIO pins
LOOPING_SENSE_PIN = 38
LOOPING_INDICATOR_PIN = 40

WIFI_SENSE_PIN = 36
WIFI_INDICATOR_PIN = 35
