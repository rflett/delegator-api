import jwt
from flask import request

from app import logger, session_scope, app
from app.Exceptions import ValidationError, ResourceNotFoundError
from app.Models import User


class AuthService(object):
    @staticmethod
    def get_user_from_request() -> User:
        """Get the user object that is claimed in the JWT payload."""
        try:
            # get token from header
            auth = request.headers['Authorization']
            token = auth.replace('Bearer ', '')
            # decode JWT
            decoded = jwt.decode(
                jwt=token,
                key=app.config['JWT_SECRET'],
                audience='backburner.online',
                algorithms='HS256'
            )
            # return user in claim or 404 if they are disabled
            with session_scope() as session:
                user = session.query(User).filter_by(id=decoded['claims']['user_id'], deleted=None).first()
                if user is None:
                    raise ResourceNotFoundError("User in JWT claim does not exist, they might be disabled.")
                else:
                    return user
        except (KeyError, AttributeError):
            raise ValidationError("Invalid request.")
        except Exception as e:
            logger.error(str(e))
            logger.info(f"Decoding raised {e}, we probably failed to decode the JWT due to a user secret/aud issue.")
            raise ValidationError("Couldn't validate the JWT.")
