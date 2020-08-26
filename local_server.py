from flask import Flask, request
from . import main

app = Flask(__name__)


@app.route('/auth', methods=['POST'])
def auth():
    return main._auth(request)


@app.route('/meta', methods=['GET'])
def meta():
    return main._meta(request)


@app.route('/data', methods=['GET', 'POST'])
def data():
    return main._data(request)
