from .app import flask_app
from .root import *

def launch_toddler_transducer():
    from waitress import serve
    serve(flask_app, host="0.0.0.0", port=8080)

def launch_dev_toddler_transducer():
    flask_app.run()
