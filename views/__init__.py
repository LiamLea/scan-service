from flask import Flask
from .scan import blue_scan
from .probe import blue_probe

app = Flask("Scan")

app.register_blueprint(blue_scan)
app.register_blueprint(blue_probe)


