"""
GPIO

General module to handle the GPIO requirements
"""
import time
from multiprocessing.managers import DictProxy

from RPi import GPIO

from config import LOOPING_SENSE_PIN, LOOPING_INDICATOR_PIN, WIFI_SENSE_PIN, WIFI_INDICATOR_PIN

GPIO.setmode(GPIO.BOARD)

class LEDSwitch:
    def __init__(self, sense_pin: int, indicator_pin: int):
        self.sense_pin = sense_pin
        self.indicator_pin = indicator_pin
        GPIO(self.sense_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO(self.indicator_pin, GPIO.OUT)
        self.indicator_status = False
        self.was_high = False

    def update_led(self):
        GPIO.output(self.indicator_pin, self.indicator_status)

    def toggle(self):
        self.indicator_status = not self.indicator_status
        self.update_led()

    def switch_on(self):
        self.indicator_status = True
        self.update_led()

    def switch_off(self):
        self.indicator_status = False
        self.update_led()

    def get_input(self):
        return GPIO.input(self.sense_pin)

    def update(self):
        if self.get_input() == GPIO.LOW:
            if self.was_high:
                self.toggle()
            self.was_high = False
        else:
            self.was_high = True


def gpio_update_loop(wifi_manager: DictProxy, vlc_playback_manager: DictProxy):
    looping_switch = LEDSwitch(LOOPING_SENSE_PIN, LOOPING_INDICATOR_PIN)
    wifi_switch = LEDSwitch(WIFI_SENSE_PIN, WIFI_INDICATOR_PIN)

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

        time.sleep(0.5)
