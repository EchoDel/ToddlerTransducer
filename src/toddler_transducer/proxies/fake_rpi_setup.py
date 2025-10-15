"""
Proxies Fake RPI Setup

Sets up the fake gpio if its not running on the r pi.
"""
import platform
import sys

if platform.machine() != 'aarch64':
    import toddler_transducer.proxies.fake_raspberry_pi

    sys.modules['RPi'] = toddler_transducer.proxies.fake_raspberry_pi     # Fake RPi
    sys.modules['RPi.GPIO'] = toddler_transducer.proxies.fake_raspberry_pi.GPIO # Fake GPIO
