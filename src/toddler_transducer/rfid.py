"""
RFID

Module containing the code for the reading the RFID tag with the MFRC522 board
"""
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


def get_and_log_rfid_id() -> int | None:
    """
    Gets the current RFID ID sector from the reader and logs it to be used later

    Returns:
        (int): The ID of the RFID tag
    """
    global CURRENT_ID
    id = get_rfid_id()
    CURRENT_ID = id
    return id


def get_logged_rfid_id() -> int | None:
    """
    Gets the logged rfid id

    Returns:
        (int): The ID of the RFID tag
    """
    return CURRENT_ID


def threaded_get_rfid_id(rfid_tag_proxy: ValueProxy):
    rfid_id = get_rfid_id()
    rfid_tag_proxy.value = rfid_id
