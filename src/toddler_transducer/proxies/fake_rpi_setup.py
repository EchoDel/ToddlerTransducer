"""
Proxies Fake RPI Setup

Sets up the fake gpio if its not running on the r pi.
"""
import platform
import sys

if platform.machine() != 'aarch64':
    import fake_rpi

    sys.modules['RPi'] = fake_rpi.RPi     # Fake RPi
    sys.modules['RPi.GPIO'] = fake_rpi.RPi.GPIO # Fake GPIO
    sys.modules['smbus'] = fake_rpi.smbus # Fake smbus (I2C)
    fake_rpi.toggle_print(False)
