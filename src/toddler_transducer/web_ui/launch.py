from multiprocessing.managers import ValueProxy

from .app import flask_app
from .root import add_root_routes
from ..multithreading_proxy import MultithreadingValueProxy


def launch_toddler_transducer_web_app(rfid_tag_proxy: ValueProxy = None):
    if rfid_tag_proxy is None:
        rfid_tag_proxy = MultithreadingValueProxy()
    from waitress import serve
    add_root_routes(flask_app, rfid_tag_proxy)
    serve(flask_app, host="0.0.0.0", port=8080)


def launch_dev_toddler_transducer_web_app(rfid_tag_proxy: ValueProxy = None):
    if rfid_tag_proxy is None:
        rfid_tag_proxy = MultithreadingValueProxy()
    add_root_routes(flask_app, rfid_tag_proxy)
    flask_app.run(host="0.0.0.0", port=8080)
