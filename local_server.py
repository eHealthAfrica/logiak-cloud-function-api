from flask import Flask, request
from . import main

app = Flask(__name__)


@app.route('/<path:text>', methods=['GET', 'POST'])
def all(text):
    if text.startswith('auth'):
        return main._auth(request)
    if text.startswith('meta'):
        return main._meta(request)
    if text.startswith('data'):
        return main._data(request)
