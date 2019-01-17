from app import app
from functools import wraps
from flask import Response, request
from app.Controllers import AuthController


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


@app.route('/login', methods=['POST'])
def login():
    return AuthController.login(request.get_json())


@app.route('/health', methods=['GET'])
def health():
    return Response(status=200)


@app.route('/secret', methods=['GET'])
@requires_jwt
def secret():
    return "Shhhh.."
