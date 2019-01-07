from flask import Response
from app import app


@app.route('/')
def index():
    return "Hello, World!"


@app.route('/health')
def health():
    return Response(status=200)


def something(x, y):
    return x * y
