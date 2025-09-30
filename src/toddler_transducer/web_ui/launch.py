"""
Web UI Launch

Launch the web app to play audio.
"""
from multiprocessing.managers import ValueProxy, DictProxy

from .app import flask_app
from .root import add_root_routes
from ..multithreading_proxy import MultithreadingValueProxy


def launch_toddler_transducer_web_app(rfid_tag_proxy: ValueProxy = None, vlc_playback_manager: DictProxy = None):
    """
    Launch the web app through waitress as a "production" environment,

    Args:
        rfid_tag_proxy (ValueProxy, Optional): The rfid tag proxy to be used to get the current tag id from the reader.
            if not provided a moke is used instead with a fixed value.
    """
    if rfid_tag_proxy is None:
        rfid_tag_proxy = MultithreadingValueProxy()
    from waitress import serve
    add_root_routes(flask_app, rfid_tag_proxy, vlc_playback_manager)
    serve(flask_app, host="0.0.0.0", port=8080)


def launch_dev_toddler_transducer_web_app(rfid_tag_proxy: ValueProxy = None, vlc_playback_manager: DictProxy = None):
    """
    Launch the web app through flask to develop,

    Args:
        rfid_tag_proxy (ValueProxy, Optional): The rfid tag proxy to be used to get the current tag id from the reader.
            if not provided a moke is used instead with a fixed value.
    """
    if rfid_tag_proxy is None:
        rfid_tag_proxy = MultithreadingValueProxy()
    add_root_routes(flask_app, rfid_tag_proxy, vlc_playback_manager)
    flask_app.run(host="0.0.0.0", port=8080)
