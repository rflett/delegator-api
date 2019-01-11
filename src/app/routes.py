import json
from app import app
from flask import Response, request
from app.Controllers import JWTController, UserController


@app.route('/')
def index():
    return "Hello World!"


@app.route('/health')
def health():
    return Response(status=200)


@app.route('/login', methods=['POST'])
def login():
    req = request.get_json()
    logged_in_user = UserController.get_user(req.get('username'), req.get('password'))

    return Response(
        "Welcome!",
        status=200,
        headers={
            "auth": JWTController.get_jwt(logged_in_user)
        }
    )


@app.route('/secret', methods=['GET'])
def secret():
    token = request.headers.get('auth')
    if token is None:
        return Response("Nope", status=403)
    else:
        decoded = JWTController.validate(token)
        return Response(json.dumps(decoded), status=200)
