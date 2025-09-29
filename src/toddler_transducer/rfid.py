"""
RFID

Module containing the code for the reading the RFID tag with the MFRC522 board
"""
import time
from multiprocessing.managers import ValueProxy

from mfrc522 import SimpleMFRC522

reader = SimpleMFRC522()
CURRENT_ID = None


def get_rfid_id() -> int | None:
    """
    Gets the current RFID ID sector from the reader

    Returns:
        (int): The ID of the RFID tag
    """
    id = reader.read_id_no_block()
    if id is None:
        id = reader.read_id_no_block()
    return id


def threaded_get_rfid_id(rfid_tag_proxy: ValueProxy):
    while True:
        rfid_id = get_rfid_id()
        rfid_tag_proxy.value = rfid_id
        time.sleep(2)
