from functools import wraps

from app.Services import AuthService
from app.Models import User

auth_service = AuthService()


def requires_jwt(f):
    """
    Decorator that checks that the request contains a JWT token in the Authorization header.
    This won't validate the user, just make sure there is a token.
    :return: Either a response (usually 401) or the decorated function.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        req_user = auth_service.get_requester_details()
        return f(req_user=req_user, *args, **kwargs)
    return decorated


def authorize(operation: str, resource: str):
    def decorator(f):
        @wraps(f)
        def wrapped_func(*args, **kwargs):
            req_user = kwargs['req_user']
            if isinstance(req_user, User):
                req_user.is_active()
            auth_scope = req_user.can(operation, resource)
            return f(auth_scope=auth_scope, *args, **kwargs)
        return wrapped_func
    return decorator
