"""
MFRC522 proxy

Module containing the code needed to proxy the MFRC522 rfid reader class when not on a raspberry pi.
"""
import random
from typing import Optional

def validate_value(value_chance: float, value_name: str):
    """
    Validates a value is within the allowed range.

    Args:
        value_chance (float): The chance of changing the value.
        value_name (str): The name of the value to validate.
    """
    if value_chance is not None:
        if (value_chance < 0) or (value_chance > 1):
            raise ValueError(f'{value_name} should be between 0 and 1, {value_chance} has been given')


class SimpleMFRC522Proxy:
    """
    Simple class to proxy the MFRC522 rfid reader.

    Attributes:
        always_none (bool): Whether the rfid reader proxy should always return None.
        persist_value_chance (Optional[float]): The chance of changing the value.
        returned_value_chance Optional[float]: The chance of the value being not None.
    """
    def __init__(self,
                 always_none: bool = True,
                 persist_value_chance: Optional[float] = None,
                 returned_value_chance: Optional[float] = None,):
        self.previous_value = None
        self.always_none = always_none

        validate_value(persist_value_chance, 'persist_value_chance')
        self.persist_value_chance = persist_value_chance

        validate_value(returned_value_chance, 'returned_value_chance')
        self.returned_value_chance = returned_value_chance

    def read_id_no_block(self) -> int | None:
        """
        Simulates the read of the rfid device.

        Returns:
            int | None: The id of the device
        """
        if self.always_none:
            return self.previous_value

        if self.persist_value_chance is not None:
            if random.random() < self.persist_value_chance:
                return self.previous_value

        if random.random() > self.returned_value_chance:
            return None

        self.previous_value = None
        return self.previous_value
