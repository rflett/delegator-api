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


def _invalidate_jwt(token: str) -> None:
    raise NotImplementedError


class AuthController(object):
    @staticmethod
    def login(req: dict) -> Response:
        """ Login """
        from app.Controllers import ValidationController, UserController

        email = req.get('email', None)
        password = req.get('password', None)

        # validate email
        email_validate_res = ValidationController.validate_email(email)
        if isinstance(email_validate_res, Response):
            return email_validate_res

        # validate password
        password_validate_res = ValidationController.validate_password(password)
        if isinstance(password_validate_res, Response):
            return password_validate_res

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

    @staticmethod
    def validate_jwt(token: str) -> bool:
        """ Returns the JWT payload if decode is successful, otherwise returns False """
        try:
            jwt.decode(jwt=token, key=app.config['JWT_SECRET'], algorithms='HS256')
            return True
        except Exception as e:
            # _invalidate_jwt(token)
            return False

    @staticmethod
    def check_authorization_header(auth: str) -> typing.Union[bool, Response]:
        from app.Controllers import AuthController

        def unauthenticated(message: str) -> Response:
            return Response(message, status=403)

        if auth is None:
            return unauthenticated("Missing Authorization header.")
        elif not isinstance(auth, str):
            return unauthenticated(f"Expected Authorization header type int got {type(auth)}.")
        elif not AuthController.validate_jwt(auth.replace('Bearer ', '')):
            return unauthenticated("Invalid token.")

        return True
