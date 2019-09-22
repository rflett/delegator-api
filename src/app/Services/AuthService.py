import jwt
from flask import request

from app import logger, session_scope
from app.Exceptions import ValidationError, ResourceNotFoundError
from app.Models import User


class AuthService(object):
    @staticmethod
    def get_user_from_request() -> User:
        """Get the user object that is claimed in the JWT payload."""
        # get auth from request
        try:
            auth = request.headers['Authorization']
            assert isinstance(auth, str)
            token = auth.replace('Bearer ', '')
        except (KeyError, AssertionError):
            raise ValidationError("Invalid request")

        try:
            # decode the token without verifying against the org key
            suspect_jwt = jwt.decode(jwt=token, algorithms='HS256', verify=False)

            # get user_id from claims
            try:
                user_id = suspect_jwt['claims']['user_id']

                with session_scope() as session:
                    user = session.query(User).filter_by(id=user_id, deleted=None).first()
                if user is None:
                    raise ResourceNotFoundError(f"User with id {user_id} does not exist.")
                else:
                    jwt.decode(jwt=token, key=user.orgs.jwt_secret, audience=user.orgs.jwt_aud, algorithms='HS256')
                    return user
            except KeyError:
                raise ValidationError("Couldn't validate the JWT.")

        except Exception as e:
            logger.error(str(e))
            logger.info(f"Decoding raised {e}, we probably failed to decode the JWT due to a user secret/aud issue.")
            raise ValidationError("Couldn't validate the JWT.")
