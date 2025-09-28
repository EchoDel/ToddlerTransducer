import signal
import time
from multiprocessing import Process, Manager

import RPi.GPIO

from toddler_transducer.rfid import threaded_get_rfid_id
from .puck_playback import puck_playback_loop
from .web_ui.launch import launch_toddler_transducer_web_app


def main():
    def term_handler(signum, frame):
        print("sig term handler")
        RPi.GPIO.cleanup()

    signal.signal(signal.SIGTERM, term_handler)

    rfid_tag_proxy = Manager().Value('i', None)  # https://dnmtechs.com/appending-to-list-with-multiprocessing-in-python-3/
    # Start the rfid process
    rfid_process = Process(target=threaded_get_rfid_id, args=(rfid_tag_proxy,))
    rfid_process.start()

    # Start the puck playback loop
    puck_playback_process = Process(target=puck_playback_loop, args=(rfid_tag_proxy,))
    puck_playback_process.start()

    # Start the flask app
    puck_playback_process = Process(target=launch_toddler_transducer_web_app, args=(rfid_tag_proxy,))
    puck_playback_process.start()
    while True:
        time.sleep(100000)  # Main loop has to keep running until all the process finish
