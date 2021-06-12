from functools import wraps

import jwt
import structlog
from flask import request, current_app
from sentry_sdk import configure_scope

from app.Extensions.Database import session_scope
from app.Extensions.Errors import ResourceNotFoundError, AuthenticationError
from app.Models.Dao import User

log = structlog.getLogger()


def requires_jwt(f):
    """
    Decorator that checks that the request contains a JWT token in the Authorization header.
    This won't validate the user, just make sure there is a token.
    :return: Either a response (usually 401) or the decorated function.
    """

    @wraps(f)
    def decorated(*args, **kwargs):
        req_user = _get_requester_details()
        return f(req_user=req_user, *args, **kwargs)

    return decorated


def authorize(operation: str, resource: str):
    def decorator(f):
        @wraps(f)
        def wrapped_func(*args, **kwargs):
            req_user: User = kwargs["req_user"]
            if not req_user.is_service_account:
                req_user.is_active()
            auth_scope = req_user.can(operation, resource)
            return f(auth_scope=auth_scope, *args, **kwargs)

        return wrapped_func

    return decorator


def _get_requester_details() -> User:
    """Determine the requester and return their object"""
    try:
        # get token from header
        auth = request.headers["Authorization"]
        token = auth.replace("Bearer ", "")
        # decode JWT
        decoded = jwt.decode(
            jwt=token, key=current_app.config["JWT_SECRET"], audience="delegator.com.au", algorithms="HS256"
        )
    except (KeyError, AttributeError) as e:
        raise AuthenticationError(f"Invalid request - {e}")
    except Exception as e:
        log.error(str(e))
        log.info(f"Decoding JWT raised {e}")
        raise AuthenticationError("Couldn't validate the JWT.")

    with configure_scope() as sentry_scope:

        if decoded["claims"]["type"] == "user":
            sentry_scope.set_user({"id": str(decoded["claims"]["user-id"]), "email": decoded["claims"]["email"]})
            return _get_user(decoded["claims"]["user-id"])
        elif decoded["claims"]["type"] == "service-account":
            sentry_scope.set_user({"id": str(decoded["claims"]["service-account-name"])})
            return _get_service_account(decoded["claims"]["service-account-name"])
        else:
            raise AuthenticationError("Can't determine requester type from token.")


def _get_user(user_id: int) -> User:
    """Get the user object that is claimed in the JWT payload."""
    # return user in claim or 404 if they are disabled
    with session_scope() as session:
        user = session.query(User).filter_by(id=user_id, deleted=None, is_service_account=False).first()
        if user is None:
            raise ResourceNotFoundError("User in JWT claim either doesn't exist or is deleted.")
        else:
            return user


def _get_service_account(role: str) -> User:
    """Get the user object for an SA based on the role"""
    with session_scope() as session:
        user = session.query(User).filter_by(role=role, is_service_account=True).first()
        if user is None:
            raise ResourceNotFoundError(f"Service account {role} doesn't exist.")
        else:
            return user
