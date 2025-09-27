"""
RFID

Module containing the code for the reading the RFID tag with the MFRC522 board
"""
from mfrc522 import MFRC522

CURRENT_ID = None


def uid_to_num(uid):
    n = 0
    for i in range(0, 5):
        n = n * 256 + uid[i]
    return n

def get_rfid_id() -> int:
    """
    Gets the current RFID ID sector from the reader

    Returns:
        (int): The ID of the RFID tag
    """
    reader = MFRC522()
    (status, TagType) = reader.MFRC522_Request(reader.PICC_REQIDL)
    if status != reader.MI_OK:
        reader.Close_MFRC522()
        return None
    (status, uid) = reader.MFRC522_Anticoll()
    if status != reader.MI_OK:
        reader.Close_MFRC522()
        return None

    reader.Close_MFRC522()
    return uid_to_num(uid)



def get_and_log_rfid_id() -> int:
    """
    Gets the current RFID ID sector from the reader and logs it to be used later

    Returns:
        (int): The ID of the RFID tag
    """
    global CURRENT_ID
    id = get_rfid_id()
    CURRENT_ID = id
    return id


def get_logged_rfid_id() -> int:
    """
    Gets the logged rfid id

    Returns:
        (int): The ID of the RFID tag
    """
    return CURRENT_ID
