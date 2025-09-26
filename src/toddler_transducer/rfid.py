"""
RFID

Module containing the code for the reading the RFID tag with the MFRC522 board
"""

from mfrc522 import SimpleMFRC522

reader = SimpleMFRC522()

def get_rfid_id():
    id, _ = reader.read()
    return id
