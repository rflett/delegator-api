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


def _unauthenticated(message: str) -> Response:
    return Response(message, status=403)


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


class AuthController(object):
    def invalidate_jwt(self, token: str = None, payload: dict = None) -> None:
        from app.Controllers import BlacklistedTokenController
        if token is not None:
            from app.Controllers import AuthController
            payload = AuthController.validate_jwt(token.replace('Bearer ', ''))
            self.invalidate_jwt(payload=payload)
        elif payload is not None:
            if payload.get('jti') is None:
                pass
            blacklist_id = f"{payload.get('aud')}:{payload.get('jti')}"
            BlacklistedTokenController.blacklist_token(blacklist_id)

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
    def logout(headers: dict) -> Response:
        """ Logout """
        from app.Controllers import AuthController
        auth = headers.get('Authorization', None)
        payload = AuthController.validate_jwt(auth.replace('Bearer ', ''))
        if payload is False:
            return _unauthenticated('Invalid token.')
        else:
            AuthController().invalidate_jwt(payload=payload)
            return Response('Logged out')

    @staticmethod
    def validate_jwt(token: str) -> typing.Union[bool, dict]:
        """ Returns the payload if decode is successful, otherwise returns False """
        from app.Controllers import BlacklistedTokenController
        try:
            suspect_jwt = jwt.decode(jwt=token, algorithms='HS256', verify=False)

            # check if aud:jti is blacklisted
            blacklist_id = f"{suspect_jwt.get('aud')}:{suspect_jwt.get('jti')}"
            if BlacklistedTokenController.is_token_blacklisted(blacklist_id):
                return False

            # check username exists, is valid
            username = suspect_jwt.get('claims').get('username')
            if username is not None:
                from app.Controllers import UserController
                user = UserController.get_user_by_username(username)
                return jwt.decode(jwt=token, key=user.get_jwt_secret(), audience=user.get_aud(), algorithms='HS256')
            else:
                AuthController().invalidate_jwt(token=token)
                return False
        except Exception as e:
            AuthController().invalidate_jwt(token=token)
            return False

    @staticmethod
    def check_authorization_header(auth: str) -> typing.Union[bool, Response]:
        from app.Controllers import AuthController

        if auth is None:
            return _unauthenticated("Missing Authorization header.")
        elif not isinstance(auth, str):
            return _unauthenticated(f"Expected Authorization header type str got {type(auth)}.")
        elif AuthController.validate_jwt(auth.replace('Bearer ', '')) is False:
            return _unauthenticated("Invalid token.")

        return True
