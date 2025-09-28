from multiprocessing import Process

from .app import flask_app
from .root import *
from ..__main__ import main


def launch_toddler_transducer():
    main()
    from waitress import serve
    serve(flask_app, host="0.0.0.0", port=8080)


def launch_dev_toddler_transducer():
    flask_app.run()
