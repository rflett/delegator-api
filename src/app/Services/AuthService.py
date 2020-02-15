import typing

import jwt
from flask import request, current_app
from aws_xray_sdk.core import xray_recorder
from sentry_sdk import configure_scope

from app.Extensions.Database import session_scope
from app.Extensions.Errors import ResourceNotFoundError, AuthorizationError
from app.Models import User
from app.Models.RBAC import ServiceAccount


class AuthService(object):
    def get_requester_details(self) -> typing.Union[User, ServiceAccount]:
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
            raise AuthorizationError(f"Invalid request - {e}")
        except Exception as e:
            current_app.logger.error(str(e))
            current_app.logger.info(f"Decoding JWT raised {e}")
            raise AuthorizationError("Couldn't validate the JWT.")

        document = xray_recorder.current_segment()
        with configure_scope() as sentry_scope:

            if decoded["claims"]["type"] == "user":
                document.set_user(str(decoded["claims"]["user-id"]))
                sentry_scope.set_user({"id": str(decoded["claims"]["user-id"]), "email": decoded["claims"]["email"]})
                return self._get_user(decoded["claims"]["user-id"])
            elif decoded["claims"]["type"] == "service-account":
                document.set_user(str(decoded["claims"]["service-account-name"]))
                sentry_scope.set_user({"id": str(decoded["claims"]["service-account-name"])})
                return ServiceAccount(decoded["claims"]["service-account-name"])
            else:
                raise AuthorizationError("Can't determine requester type from token.")

    @staticmethod
    def _get_user(user_id: int) -> User:
        """Get the user object that is claimed in the JWT payload."""
        # return user in claim or 404 if they are disabled
        with session_scope() as session:
            user = session.query(User).filter_by(id=user_id, deleted=None).first()
            if user is None:
                raise ResourceNotFoundError("User in JWT claim either doesn't exist or is disabled.")
            else:
                return user
