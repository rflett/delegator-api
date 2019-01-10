import jwt
import typing
from app import app


_common_payload = {
    "common": "payload"
}


class JWTController(object):

    @staticmethod
    def get_jwt(payload: typing.Union[dict, None] = None) -> str:
        """ Returns an encoded JWT token """
        if payload is None:
            payload = {}
        return jwt.encode(
            payload={
                **_common_payload,
                **payload
            },
            key=app.config['JWT_SECRET'],
            algorithm='HS256'
        )

    @staticmethod
    def validate(token: str) -> typing.Union[dict, bool]:
        """ Returns the JWT payload if decode is successful, otherwise returns False """
        try:
            return jwt.decode(jwt=token, key=app.config['JWT_SECRET'], algorithms='HS256')
        except Exception as e:
            return False

    @staticmethod
    def invalidate_token(token: str) -> None:
        raise NotImplementedError
