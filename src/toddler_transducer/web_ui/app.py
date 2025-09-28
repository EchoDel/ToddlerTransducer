import os

from flask import Flask

flask_app = Flask(__name__)
flask_app.config["SESSION_PERMANENT"] = False
flask_app.config["SECRET_KEY"] = os.urandom(32)
