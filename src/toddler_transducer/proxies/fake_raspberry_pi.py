"""
Fake Raspberry Pi

Module to replicate the raspberry pi package when not installed on a raspberry pi.
"""
from random import randint
from functools import wraps

PRINT_ON = False
RANDOMIZE_INPUT = False


def switch_print(p: bool):
    """
    Toggle the print of the fake raspberry pi usage.

    Args:
        p (bool): The print status, if True then prints each time a fake raspberry pi interface is used
    """
    global PRINT_ON
    PRINT_ON = p


def printf(f):
    """Decorator that prints function calls when PRINT_ON is True."""
    @wraps(f)
    def wrapped(*args, **kwargs):
        r = f(*args, **kwargs)

        if len(args):
            c = str(args[0].__class__).split('\'')[1]  # grab self from the class method
        else:
            c = ''  # no class

        if PRINT_ON:
            if r:
                print('{}.{}{}: {}'.format(c, f.__name__, args[1:], r))
            else:
                print('{}.{}{}'.format(c, f.__name__, args[1:]))
        return r
    return wrapped


def switch_randomize_inputs(p: bool):
    """
    Toggle the randomization of the fake raspberry pi inputs.

    Args:
        p (bool): The randomization approach, if True then inputs are randomized each time a fake raspberry pi
         interface is used.
    """
    global RANDOMIZE_INPUT
    RANDOMIZE_INPUT = p


class Base:
    """Base class that prints a warning when using fake Raspberry Pi interfaces."""

    def __init__(self, name: str | None = None) -> None:
        print('<<< WARNING: using fake raspberry pi interfaces >>>')
        if name:
            print(f'<<< Using: {name} >>>')


class _GPIO(Base):

    class PWM(Base):
        """Software PWM emulation."""

        @printf
        def __init__(self, channel: int = 0, frequency: int = 0) -> None:
            Base.__init__(self, self.__class__)

        @printf
        def start(self, dc: float) -> None:
            """Start PWM with the given duty cycle."""

        def stop(self) -> None:
            """Stop PWM."""

        def ChangeDutyCycle(self, dc: float) -> None:
            """Change the PWM duty cycle."""

        def ChangeFrequency(self, frequency: int) -> None:
            """Change the PWM frequency."""

    # Values
    LOW = 0
    HIGH = 1

    # Modes
    BCM = 11
    BOARD = 10

    # Pull
    PUD_OFF = 20
    PUD_DOWN = 21
    PUD_UP = 22

    # Edges
    RISING = 31
    FALLING = 32
    BOTH = 33

    # Functions
    OUT = 0
    IN = 1
    SERIAL = 40
    SPI = 41
    I2C = 42
    HARD_PWM = 43
    UNKNOWN = -1

    # Versioning
    RPI_REVISION = 2
    VERSION = '0.5.6'

    def __init__(self) -> None:
        """Initialise the fake GPIO with 40 input pins."""
        Base.__init__(self, self.__class__)
        self._inputs = [None] * 40  # We have 40 input pins

    @printf
    def setwarnings(self, a: bool) -> None:
        """Set GPIO warning state (no-op in fake)."""

    @printf
    def setmode(self, a: int) -> None:
        """Set GPIO mode (no-op in fake)."""

    @printf
    def getmode(self) -> int:
        """Return the BCM mode constant."""
        return GPIO.BCM

    @printf
    def setup(self, channel: int, state: int, initial: int = 0, pull_up_down: int | None = None) -> None:
        """Set up a GPIO channel (no-op in fake)."""

    @printf
    def input(self, channel: int) -> int:
        """Read a GPIO input value.

        Returns:
            int: The manually set value, a random value, or 0.
        """
        if 0 <= channel < len(self._inputs) and self._inputs[channel] is not None:
            return self._inputs[channel]
        if RANDOMIZE_INPUT:
            return randint(0, 1)
        return 0

    @printf
    def set_input(self, channel: int, value: int) -> None:
        """Manually set a GPIO input pin value."""
        self._inputs[channel] = value

    @printf
    def cleanup(self, a: int | None = None) -> None:
        """Clean up GPIO channels (no-op in fake)."""

    @printf
    def output(self, channel: int, state: int) -> None:
        """Set a GPIO output value (no-op in fake)."""

    @printf
    def wait_for_edge(self, channel: int, edge: int) -> None:
        """Wait for a GPIO edge (no-op in fake)."""

    @printf
    def add_event_detect(self, channel: int, edge: int, callback=None, bouncetime: int | None = None) -> None:
        """Add edge detection (no-op in fake)."""

    @printf
    def add_event_callback(self, channel: int, callback=None) -> None:
        """Add edge callback (no-op in fake)."""

    @printf
    def remove_event_detect(self, channel: int) -> None:
        """Remove edge detection (no-op in fake)."""

    @printf
    def event_detected(self, channel: int) -> bool:
        """Check if an event has been detected (always False in fake)."""
        return False

    @printf
    def gpio_function(self, channel: int) -> int:
        """Return the OUT function constant."""
        return GPIO.OUT


GPIO = _GPIO()
