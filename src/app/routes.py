import json
from app import app
from flask import Response, request
from app.Controllers import JWTController


@app.route('/')
def index():
    return "Hello World!"


@app.route('/health')
def health():
    return Response(status=200)


@app.route('/login', methods=['POST'])
def login():
    req = request.get_json()
    user = req.get('user')
    password = req.get('password')
    if user == 'user' and password == 'password':
        encoded = JWTController.get_jwt({'extra': 'payload'})
        return Response(
            "Welcome!",
            status=200,
            headers={
                "auth": encoded
            }
        )
    else:
        return Response("Missing auth", status=403)


@app.route('/secret', methods=['GET'])
def secret():
    token = request.headers.get('auth')
    if token is None:
        return Response("Nope", status=403)
    else:
        decoded = JWTController.validate(token)
        return Response(json.dumps(decoded), status=200)
