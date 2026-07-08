"""
Web UI Launch

Launch the web app to play audio.
"""
from multiprocessing.managers import ValueProxy, DictProxy

from toddler_transducer.web_ui.app import flask_app
from toddler_transducer.web_ui.root import add_root_routes
from toddler_transducer.proxies.multithreading_proxy import MultithreadingValueProxy


def launch_toddler_transducer_web_app(rfid_tag_proxy: ValueProxy | None = None,
                                      vlc_playback_manager: DictProxy | None = None) -> None:
    """Launch the web app through Waitress (production).

    Args:
        rfid_tag_proxy: Proxy for the current RFID tag id. A mock is used when None.
        vlc_playback_manager: Shared dict for VLC control and state.
    """
    if rfid_tag_proxy is None:
        rfid_tag_proxy = MultithreadingValueProxy()
    from waitress import serve
    add_root_routes(flask_app, rfid_tag_proxy, vlc_playback_manager)
    print(f'Launching server at https://localhost:8080')
    serve(flask_app, host="0.0.0.0", port=8080)


def launch_dev_toddler_transducer_web_app(rfid_tag_proxy: ValueProxy | None = None,
                                          vlc_playback_manager: DictProxy | None = None) -> None:
    """Launch the web app through Flask (development).

    Args:
        rfid_tag_proxy: Proxy for the current RFID tag id. A mock is used when None.
        vlc_playback_manager: Shared dict for VLC control and state.
    """
    if rfid_tag_proxy is None:
        rfid_tag_proxy = MultithreadingValueProxy()
    add_root_routes(flask_app, rfid_tag_proxy, vlc_playback_manager)
    flask_app.run(host="0.0.0.0", port=8080)
