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

# AI model backend selection — "hunyuan3d" or "instantmesh"
AI_MODEL_BACKEND = "hunyuan3d"

# GPIO pins
LOOPING_SENSE_PIN = 38
LOOPING_INDICATOR_PIN = 40

WIFI_SENSE_PIN = 36
WIFI_INDICATOR_PIN = 35

# Rotary encoder pins (BOARD numbering)
ENCODER_CLK_PIN = 5
ENCODER_DT_PIN = 7
ENCODER_VOLUME_NOTCH_PER_STEP = 4
ENCODER_VOLUME_INCREASE_PER_STEP = 4

