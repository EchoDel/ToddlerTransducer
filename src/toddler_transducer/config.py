"""
Config

Module containing the config for the application
"""
from pathlib import Path

AUDIO_FILE_BASE_PATH = Path('./audio_files')
METADATA_FILE_PATH = AUDIO_FILE_BASE_PATH / 'metadata'
BACKUP_FILE_BASE_PATH = Path('./backups')
BACKUP_FILE_BASE_PATH.mkdir(parents=True, exist_ok=True)

VOLUME_FILE_PATH = Path('./persistent_settings.json')

# GPIO pins
LOOPING_SENSE_PIN = 38
LOOPING_INDICATOR_PIN = 40

WIFI_SENSE_PIN = 36
WIFI_INDICATOR_PIN = 35

# Rotary encoder pins (BOARD numbering)
ENCODER_CLK_PIN = 3
ENCODER_DT_PIN = 4
ENCODER_VOLUME_STEPS_PER_NOTCH = 4
