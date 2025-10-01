"""
Main

Contains the main function which setups up all the subprocess and controls the flow of data between them.
"""
import signal
import time
import sys
from multiprocessing import Process, Manager

from toddler_transducer.rfid import threaded_get_rfid_id
from .audio import VLCControlDict, launch_vlc_threaded
from .puck_playback import puck_playback_loop
from .web_ui.launch import launch_toddler_transducer_web_app


def main():
    """
    The main function for the program.
    This controls both the puck playback and the webapp playback through multiprocessing.
    """

    def term_handler(signum, frame):
        """
        Handles the sigterm event so that the gpio can be cleaned up if its being used.
        Based on this blog;
         * https://chadrick-kwag.net/posts/python-interrupt-sigterm-sigkill-exception-handling-experiments/

        Args:
            signum:
            frame:
        """
        print("sig term handler")
        # https://stackoverflow.com/questions/56098431/runtimewarning-this-channel-is-already-in-use
        try:
            import RPi.GPIO
            RPi.GPIO.cleanup()
        except ImportError:
            pass
        sys.exit(0)

    signal.signal(signal.SIGTERM, term_handler)

    multithread_manager = Manager()
    rfid_tag_proxy = multithread_manager.Value('i', None)
    vlc_playback_manager: VLCControlDict = multithread_manager.dict(
        {'play_rfid_id': False,
        'play_track_name': False,
        'do_play': False,
        'do_stop': False,
        'do_pause': False,
        'toggle_looping': False,

        # State outputs
        'playback_source': None,
        'is_playing': None,
        'is_looping': None,
        'current_playing_track_uuid': None,
        'track_length': None,
        'track_time_through': None,
        })

    wifi_manager: VLCControlDict = multithread_manager.dict(
        {'wifi_state': False,
         })

    # Start the rfid process
    rfid_process = Process(target=threaded_get_rfid_id, args=(rfid_tag_proxy,))
    rfid_process.start()

    # Start the vlc process
    puck_playback_process = Process(target=launch_vlc_threaded, args=(vlc_playback_manager, ))
    puck_playback_process.start()

    # Start the puck playback loop
    puck_playback_process = Process(target=puck_playback_loop, args=(rfid_tag_proxy, vlc_playback_manager))
    puck_playback_process.start()

    # Start the flask app
    puck_playback_process = Process(target=launch_toddler_transducer_web_app, args=(rfid_tag_proxy, vlc_playback_manager))
    puck_playback_process.start()
    while True:
        time.sleep(100000)  # Main loop has to keep running until all the process finish
