"""
Pairing

Module containing the pairing code and token generation for binding a
slave device to a master device.
"""

import secrets

PAIRING_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
PAIRING_CODE_LENGTH = 6


def generate_pairing_code() -> str:
    """Generate a short human-readable pairing code.

    Returns:
        str: The pairing code.
    """
    return "".join(secrets.choice(PAIRING_ALPHABET) for _ in range(PAIRING_CODE_LENGTH))


def verify_pairing_code(provided: str, expected: str) -> bool:
    """Verify a pairing code against the expected value in constant time.

    Args:
        provided (str): The code supplied by the user.
        expected (str): The expected code.

    Returns:
        bool: True if the codes match.
    """
    return secrets.compare_digest(provided.strip().upper(), expected.strip().upper())


def generate_token() -> str:
    """Generate a random sync token.

    Returns:
        str: The hex-encoded sync token.
    """
    return secrets.token_hex(32)
