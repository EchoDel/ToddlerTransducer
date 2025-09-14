import time

from machine import Pin

from .helper_functions.wifi_connection import connect_wifi

led = Pin('LED', Pin.OUT)

def blink():
    led.on()
    time.sleep(0.1)
    led.off()
    time.sleep(0.1)


for _ in range(5):
    blink()


wifi_config_file = 'configs/wireless_network.json'

# print(connect_wifi(2, wifi_config_file))


import os
from machine import PWM
from machine import I2C
from machine import I2S
from machine import Pin

# ======= I2S CONFIGURATION =======
SCK_PIN = 1
WS_PIN = 2
SD_PIN = 4
# MCK_PIN = 5
I2S_ID = 1
BUFFER_LENGTH_IN_BYTES = 40000
# ======= I2S CONFIGURATION =======

# ======= AUDIO CONFIGURATION =======
WAV_FILE = "001014.wav"
WAV_SAMPLE_SIZE_IN_BITS = 16
FORMAT = I2S.MONO
SAMPLE_RATE_IN_HZ = 32000



audio_out = I2S(
    I2S_ID,
    sck=Pin(SCK_PIN),
    ws=Pin(WS_PIN),
    sd=Pin(SD_PIN),
    mode=I2S.TX,
    bits=WAV_SAMPLE_SIZE_IN_BITS,
    format=FORMAT,
    rate=SAMPLE_RATE_IN_HZ,
    ibuf=BUFFER_LENGTH_IN_BYTES,
)

# allocate sample array
# memoryview used to reduce heap allocation
wav_samples = bytearray(10000)
wav_samples_mv = memoryview(wav_samples)


wav = open(f"/MusicBox/{WAV_FILE}", "rb")
_ = wav.seek(44)

# continuously read audio samples from the WAV file
# and write them to an I2S DAC
print("==========  START PLAYBACK ==========")
try:
    while True:
        num_read = wav.readinto(wav_samples_mv)
        # end of WAV file?
        if num_read == 0:
            # end-of-file, advance to first byte of Data section
            _ = wav.seek(44)
        else:
            _ = audio_out.write(wav_samples_mv[:num_read])
except (KeyboardInterrupt, Exception) as e:
    print("caught exception {} {}".format(type(e).__name__, e))

# cleanup
wav.close()
audio_out.deinit()
print("Done")
