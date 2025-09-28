import signal
import sys
from collections import deque
from multiprocessing import Process


from toddler_transducer.rfid import threaded_get_rfid_id
from .puck_playback import puck_playback_loop


def main():
    def term_handler(signum, frame):
        print("sig term handler")
        sys.exit(0)

    signal.signal(signal.SIGTERM, term_handler)

    rfid_tag_id = []
    # Start the rfid process
    rfid_process = Process(target=threaded_get_rfid_id, args=(rfid_tag_id,))
    rfid_process.start()

    # Start the
    puck_playback_process = Process(target=puck_playback_loop, args=(rfid_tag_id,))
    puck_playback_process.start()
