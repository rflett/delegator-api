from app import app
from functools import wraps
from flask import Response, request
from app.Controllers import AuthController, UserController


def requires_jwt(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get('Authorization', None)
        check = AuthController.check_authorization_header(auth)
        if isinstance(check, Response):
            return check
        else:
            return f(*args, **kwargs)
    return decorated


@app.route('/health', methods=['GET'])
def health():
    return Response(status=200)


@app.route('/login', methods=['POST'])
def login():
    return AuthController.login(request.get_json())


@app.route('/logout', methods=['POST'])
@requires_jwt
def logout():
    return AuthController.logout(request.headers)


@app.route('/test_create', methods=['GET'])
def test_create():
    return UserController.test_create()
