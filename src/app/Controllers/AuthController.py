import jwt
import uuid
import typing
from app.Controllers.LogControllers import UserAuthLogController
from app.Models import User
from app.Models.Enums import UserAuthLogAction
from flask import Response


_common_payload = {
    "jti": str(uuid.uuid4())
}


def _get_jwt(user: User) -> str:
    """ Returns an encoded JWT token """
    payload = user.claims()
    jwt_secret = user.get_jwt_secret()
    if payload is None:
        payload = {}
    return jwt.encode(
        payload={
            **_common_payload,
            **payload
        },
        key=jwt_secret,
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

        # check password
        if user.check_password(password):
            UserAuthLogController.log(
                user=user,
                action=UserAuthLogAction.LOGIN
            )
            return Response(
                "Welcome.",
                headers={
                    'Authorization': f"Bearer {_get_jwt(user)}"
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
            suspect_jwt = jwt.decode(jwt=token, algorithms='HS256', verify=False)
            username = suspect_jwt.get('claims').get('username')
            if username is not None:
                from app.Controllers import UserController
                user = UserController.get_user_by_username(username)
                jwt.decode(jwt=token, key=user.get_jwt_secret(), algorithms='HS256')
                return True
            else:
                # _invalidate_jwt(token)
                return False
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
            return unauthenticated(f"Expected Authorization header type str got {type(auth)}.")
        elif not AuthController.validate_jwt(auth.replace('Bearer ', '')):
            return unauthenticated("Invalid token.")

        return True
