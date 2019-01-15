import jwt
import typing
from app import app
from flask import Response


_common_payload = {
    "common": "payload"
}


def _get_jwt(payload: typing.Union[dict, None] = None) -> str:
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
    ).decode("utf-8")


def validate_jwt(token: str) -> typing.Union[dict, bool]:
    """ Returns the JWT payload if decode is successful, otherwise returns False """
    try:
        return jwt.decode(jwt=token, key=app.config['JWT_SECRET'], algorithms='HS256')
    except Exception as e:
        return False


def invalidate_jwt(token: str) -> None:
    raise NotImplementedError


class AuthController(object):
    @staticmethod
    def login(req: dict) -> Response:
        """ Login """
        from app.Controllers import ValidationController, UserController

        email = req.get('email', None)
        password = req.get('password', None)

        # validate email
        email_validate = ValidationController.validate_email(email)
        if isinstance(email_validate, Response):
            return email_validate

        # validate password
        password_validate = ValidationController.validate_password(password)
        if isinstance(password_validate, Response):
            return password_validate

        # get user
        try:
            user = UserController.get_user_by_email(email)
        except ValueError:
            return Response("User does not exist", 400)

        # TODO actually encrypt password
        if user.password == password:
            return Response(
                "Welcome.",
                headers={
                    'Authorization': f"Bearer {_get_jwt(user.claims())}"
                }
            )
        else:
            return Response(
                "Password incorrect.",
                status=403
            )
