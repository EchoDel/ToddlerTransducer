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
    def __init__(self, name=None):
        print('<<< WARNING: using fake raspberry pi interfaces >>>')
        if name:
            print(f'<<< Using: {name} >>>')


class _GPIO(Base):

    class PWM(Base):
        @printf
        def __init__(self, channel=0, frequency=0):
            Base.__init__(self, self.__class__)

        @printf
        def start(self, dc):
            pass

        def stop(self):
            pass

        def ChangeDutyCycle(self, dc):
            pass

        def ChangeFrequency(self, frequency):
            pass

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

    def __init__(self):
        Base.__init__(self, self.__class__)
        self._inputs = [None] * 40  # We have 40 input pins

    @printf
    def setwarnings(self, a):
        pass

    @printf
    def setmode(self, a):
        pass

    @printf
    def getmode(self):
        return GPIO.BCM

    @printf
    def setup(self, channel, state, initial=0, pull_up_down=None):
        pass

    @printf
    def input(self, channel):
        if channel in self._inputs and self._inputs[channel] is not None:
            return self._inputs[channel]
        if RANDOMIZE_INPUT:
            return randint(0, 1)
        return 0

    @printf
    def set_input(self, channel, value):
        self._inputs[channel] = value

    @printf
    def cleanup(self, a=None):
        pass

    @printf
    def output(self, channel, state):
        pass

    @printf
    def wait_for_edge(self, channel, edge):
        pass

    @printf
    def add_event_detect(self, channel, edge, callback=None, bouncetime=None):
        pass

    @printf
    def add_event_callback(self, channel, callback=None):
        pass

    @printf
    def remove_event_detect(self, channel):
        pass

    @printf
    def event_detected(self, channel):
        return False

    @printf
    def gpio_function(self, channel):
        return GPIO.OUT


GPIO = _GPIO()
