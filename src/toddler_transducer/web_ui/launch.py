"""
Web UI Launch

Launch the web app to play audio.
"""

import threading
import time
from multiprocessing.managers import ValueProxy, DictProxy

from toddler_transducer.config import WEB_UI_PORT
from toddler_transducer.device_config import get_device_name, is_master
from toddler_transducer.device_sync.discovery import advertise
from toddler_transducer.device_sync.sync import sync_loop_thread
from toddler_transducer.web_ui.app import flask_app
from toddler_transducer.web_ui.devices import add_device_routes
from toddler_transducer.web_ui.root import add_root_routes
from toddler_transducer.proxies.multithreading_proxy import MultithreadingValueProxy


def start_background_services() -> None:
    """Start the sync and master advertising threads."""
    threading.Thread(target=sync_loop_thread, daemon=True).start()

    def advertise_loop() -> None:
        zeroconf_instance = None
        consecutive_failures = 0
        while True:
            if is_master() and zeroconf_instance is None:
                try:
                    zeroconf_instance = advertise(WEB_UI_PORT, get_device_name())
                    consecutive_failures = 0
                except Exception:
                    consecutive_failures += 1
                    zeroconf_instance = None
            elif not is_master() and zeroconf_instance is not None:
                try:
                    zeroconf_instance.close()
                except Exception:
                    pass
                zeroconf_instance = None
            time.sleep(min(10 * 2 ** min(consecutive_failures, 3), 60))

    threading.Thread(target=advertise_loop, daemon=True).start()


def launch_toddler_transducer_web_app(
    rfid_tag_proxy: ValueProxy | None = None, vlc_playback_manager: DictProxy | None = None
) -> None:
    """Launch the web app through Waitress (production).

    Args:
        rfid_tag_proxy: Proxy for the current RFID tag id. A mock is used when None.
        vlc_playback_manager: Shared dict for VLC control and state.
    """
    if rfid_tag_proxy is None:
        rfid_tag_proxy = MultithreadingValueProxy()
    from waitress import serve

    add_root_routes(flask_app, rfid_tag_proxy, vlc_playback_manager)
    add_device_routes(flask_app)
    start_background_services()
    print(f"Launching server at https://localhost:{WEB_UI_PORT}")
    serve(flask_app, host="0.0.0.0", port=WEB_UI_PORT)


def launch_dev_toddler_transducer_web_app(
    rfid_tag_proxy: ValueProxy | None = None, vlc_playback_manager: DictProxy | None = None
) -> None:
    """Launch the web app through Flask (development).

    Args:
        rfid_tag_proxy: Proxy for the current RFID tag id. A mock is used when None.
        vlc_playback_manager: Shared dict for VLC control and state.
    """
    if rfid_tag_proxy is None:
        rfid_tag_proxy = MultithreadingValueProxy()
    add_root_routes(flask_app, rfid_tag_proxy, vlc_playback_manager)
    add_device_routes(flask_app)
    start_background_services()
    flask_app.run(host="0.0.0.0", port=WEB_UI_PORT)
