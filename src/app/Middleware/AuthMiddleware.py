from functools import wraps

from flask import request, Response

from app import app
from app.Controllers import AuthenticationController
from app.Exceptions import AuthenticationError


def requires_jwt(f):
    """
    Decorator that checks that the request contains a JWT token in the Authorization header.
    This won't validate the user, just make sure there is a token.
    :return: Either a response (usually 401) or the decorated function.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get('Authorization', None)
        check = AuthenticationController.check_authorization_header(auth)
        if isinstance(check, Response):
            return check
        else:
            return f(*args, **kwargs)
    return decorated


def requires_token_auth(f):
    """Checks that a request contains a valid auth token"""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get('Authorization', None)
        if auth != app.config['BACKBURNER_API_KEY']:
            raise AuthenticationError("Unauthorized.")
        else:
            return f(*args, **kwargs)
    return decorated
