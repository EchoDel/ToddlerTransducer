import signal
import time
import sys
from multiprocessing import Process, Manager

import RPi.GPIO

from toddler_transducer.rfid import threaded_get_rfid_id
from .puck_playback import puck_playback_loop
from .web_ui.launch import launch_toddler_transducer_web_app


def main():
    def term_handler(signum, frame):
        """
        Handles the sigterm event so that the gpio can be cleaned up if its being used.
        Based on this blog, https://chadrick-kwag.net/posts/python-interrupt-sigterm-sigkill-exception-handling-experiments/

        Args:
            signum:
            frame:
        """
        print("sig term handler")
        # https://stackoverflow.com/questions/56098431/runtimewarning-this-channel-is-already-in-use
        RPi.GPIO.cleanup()
        sys.exit(0)

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
