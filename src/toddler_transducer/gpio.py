"""
GPIO

General module to handle the GPIO requirements
"""
import time
from multiprocessing.managers import DictProxy

from RPi import GPIO

from toddler_transducer.audio import save_volume
from toddler_transducer.config import LOOPING_SENSE_PIN, LOOPING_INDICATOR_PIN, WIFI_SENSE_PIN, WIFI_INDICATOR_PIN
from toddler_transducer.config import ENCODER_CLK_PIN, ENCODER_DT_PIN, ENCODER_VOLUME_NOTCH_PER_STEP, ENCODER_VOLUME_INCREASE_PER_STEP

GPIO.setmode(GPIO.BOARD)

class LEDSwitch:
    """
    Class to handle a momentary with an LED status indicator
    """
    def __init__(self, sense_pin: int, indicator_pin: int):
        self.sense_pin = sense_pin
        self.indicator_pin = indicator_pin
        GPIO.setup(self.sense_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.indicator_pin, GPIO.OUT)
        self.indicator_status = False
        self.was_high = False

    def update_led(self):
        """
        Sets the LED output to be that of the indicator status.
        """
        GPIO.output(self.indicator_pin, self.indicator_status)

    def toggle(self):
        """
        Toggles the state.
        """
        self.indicator_status = not self.indicator_status
        self.update_led()

    def switch_on(self):
        """
        Turns the switch on.
        """
        self.indicator_status = True
        self.update_led()

    def switch_off(self):
        """
        Turns the switch of.
        """
        self.indicator_status = False
        self.update_led()

    def get_input(self):
        """
        Gets the input from the momentary switch.
        """
        return GPIO.input(self.sense_pin)

    def update(self):
        """
        Updates the status and output. On the falling edge
        """
        if self.get_input() == GPIO.LOW:
            if self.was_high:
                self.toggle()
            self.was_high = False
        else:
            self.was_high = True


class RotaryEncoderVolume:
    """
    Reads a rotary encoder to control volume with configurable gearing.

    Args:
        clk_pin (int): BOARD pin number for the CLK output.
        dt_pin (int): BOARD pin number for the DT output.
        steps_per_notch (int): How many detent steps equal one volume increment.
    """
    def __init__(self, clk_pin: int, dt_pin: int, notch_per_step: int, volume_per_step: int):
        self.clk_pin = clk_pin
        self.dt_pin = dt_pin
        self.notch_per_step = notch_per_step
        self.volume_per_step = volume_per_step
        GPIO.setup(self.clk_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.dt_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        self.last_clk = GPIO.input(self.clk_pin)
        self.counter = 0

    def update(self, vlc_playback_manager: dict):
        """
        Reads the encoder state and adjusts volume when the step threshold is reached.
        """
        current_clk = GPIO.input(self.clk_pin)
        if current_clk != self.last_clk:
            dt_state = GPIO.input(self.dt_pin)
            if dt_state != current_clk:
                self.counter += 1
            else:
                self.counter -= 1

            if self.counter >= self.notch_per_step:
                self.counter = 0
                current_vol = vlc_playback_manager.get('volume', 50)
                new_vol = max(0, min(100, current_vol + self.volume_per_step))
                vlc_playback_manager['volume'] = new_vol
                save_volume(new_vol)
            elif self.counter <= -self.notch_per_step:
                self.counter = 0
                current_vol = vlc_playback_manager.get('volume', 50)
                new_vol = max(0, min(100, current_vol - self.volume_per_step))
                vlc_playback_manager['volume'] = new_vol
                save_volume(new_vol)

        self.last_clk = current_clk


def gpio_update_loop(wifi_manager: DictProxy, vlc_playback_manager: DictProxy):
    """
    Loops to run in a thread to handle the updating of the gpio switched with the process.

    Args:
        wifi_manager (DictProxy): The wifi manager.
        vlc_playback_manager (DictProxy): The vlc playback manager.
    """
    looping_switch = LEDSwitch(LOOPING_SENSE_PIN, LOOPING_INDICATOR_PIN)
    wifi_switch = LEDSwitch(WIFI_SENSE_PIN, WIFI_INDICATOR_PIN)
    volume_encoder = RotaryEncoderVolume(ENCODER_CLK_PIN, ENCODER_DT_PIN, ENCODER_VOLUME_NOTCH_PER_STEP, ENCODER_VOLUME_INCREASE_PER_STEP)

    while True:
        # Update the wifi switch
        wifi_switch.update()
        wifi_manager['wifi_state'] = wifi_switch.get_input()

        # Update the looping status
        if looping_switch.indicator_status != vlc_playback_manager['is_looping']:
            looping_switch.toggle()
        looping_switch.update()
        if looping_switch.indicator_status != vlc_playback_manager['is_looping']:
            vlc_playback_manager['toggle_looping'] = True
            time.sleep(5)

        volume_encoder.update(vlc_playback_manager)

        time.sleep(0.01)
