"""
RFID

Module containing the code for the reading the RFID tag with the MFRC522 board
"""
import time
from multiprocessing.managers import ValueProxy

try:
    from mfrc522 import SimpleMFRC522
    reader = SimpleMFRC522()
except ImportError:
    from toddler_transducer.proxies import SimpleMFRC522Proxy
    reader = SimpleMFRC522Proxy()


def get_rfid_id() -> int | None:
    """
    Gets the current RFID ID sector from the reader

    Returns:
        (int): The ID of the RFID tag
    """
    rfid_id = reader.read_id_no_block()
    if rfid_id is None:
        rfid_id = reader.read_id_no_block()
    return rfid_id

def threaded_get_rfid_id(rfid_tag_proxy: ValueProxy):
    """
    Gets the current RFID ID sector from the reader and adds it to the rfid_tag_proxy

    Args:
        rfid_tag_proxy (ValueProxy): The object providing a .value items which can be filled with the current rfid tag
         id.
    """
    while True:
        rfid_id = get_rfid_id()
        rfid_tag_proxy.value = rfid_id
        time.sleep(2)
