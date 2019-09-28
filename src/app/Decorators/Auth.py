from functools import wraps

from flask import request

from app import app
from app.Exceptions import AuthenticationError
from app.Services import AuthService


def requires_jwt(f):
    """
    Decorator that checks that the request contains a JWT token in the Authorization header.
    This won't validate the user, just make sure there is a token.
    :return: Either a response (usually 401) or the decorated function.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        req_user = AuthService.get_user_from_request()
        return f(req_user=req_user, *args, **kwargs)
    return decorated


def requires_token_auth(f):
    """Checks that a request contains a valid auth token"""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get('Authorization', None)
        if auth != app.config['DELEGATOR_API_KEY']:
            raise AuthenticationError("Unauthorized.")
        else:
            return f(*args, **kwargs)
    return decorated


def authorize(operation: str, resource: str):
    def decorator(f):
        @wraps(f)
        def wrapped_func(*args, **kwargs):
            req_user = kwargs['req_user']
            req_user.is_active()
            auth_scope = req_user.can(operation, resource)
            return f(auth_scope=auth_scope, *args, **kwargs)
        return wrapped_func
    return decorator
