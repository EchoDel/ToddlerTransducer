from multiprocessing.managers import ValueProxy

from .app import flask_app
from .root import add_root_routes


def launch_toddler_transducer_web_app(rfid_tag_proxy: ValueProxy):
    from waitress import serve
    add_root_routes(flask_app, rfid_tag_proxy)
    serve(flask_app, host="0.0.0.0", port=8080)


def launch_dev_toddler_transducer_web_app():
    flask_app.run()
