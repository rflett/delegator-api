import typing

import jwt
from flask import request

from app import logger, session_scope, app
from app.Exceptions import ValidationError, ResourceNotFoundError
from app.Models import User
from app.Models.RBAC import ServiceAccount


class AuthService(object):
    def get_requester_details(self) -> typing.Union[User, ServiceAccount]:
        """Determine the requester and return their object"""
        try:
            # get token from header
            auth = request.headers['Authorization']
            token = auth.replace('Bearer ', '')
            # decode JWT
            decoded = jwt.decode(
                jwt=token,
                key=app.config['JWT_SECRET'],
                audience='delegator.com.au',
                algorithms='HS256'
            )
        except (KeyError, AttributeError):
            raise ValidationError("Invalid request.")
        except Exception as e:
            logger.error(str(e))
            logger.info(f"Decoding raised {e}, we probably failed to decode the JWT due to a user secret/aud issue.")
            raise ValidationError("Couldn't validate the JWT.")

        if decoded['claims']['type'] == 'user':
            return self._get_user(decoded['claims']['user-id'])
        elif decoded['claims']['type'] == 'service-account':
            return self._get_service_account(decoded['claims']['service-account-name'])
        else:
            raise ValidationError("Can't determine requester type from token.")

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

    @staticmethod
    def _get_service_account(name: str) -> ServiceAccount:
        sa = ServiceAccount(name)
        return sa