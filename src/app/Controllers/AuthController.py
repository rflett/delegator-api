import datetime
import jwt
import typing
import uuid
from app.Controllers.LogControllers import UserAuthLogController
from app.Models import User
from app.Models.Enums import UserAuthLogAction
from flask import Response


TOKEN_TTL_IN_MINUTES = 60


def _unauthenticated(message: str) -> Response:
    return Response(message, status=403)


def _get_jwt(user: User) -> str:
    """ Returns an encoded JWT token """
    payload = user.claims()
    jwt_secret = user.jwt_secret
    if payload is None:
        payload = {}
    return jwt.encode(
        payload={
            **payload,
            "jti": str(uuid.uuid4()),
            "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=TOKEN_TTL_IN_MINUTES)
        },
        key=jwt_secret,
        algorithm='HS256'
    ).decode("utf-8")


class AuthController(object):
    @staticmethod
    def login(req: dict) -> Response:
        """ Login """
        from app.Controllers import ValidationController, UserController

        email = req.get('email')
        password = req.get('password')

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
        from app.Controllers import AuthController, UserController
        from app.Controllers.LogControllers import UserAuthLogController

        auth = headers.get('Authorization', None)
        payload = AuthController.validate_jwt(auth.replace('Bearer ', ''))

        if payload is False:
            return _unauthenticated('Invalid token.')
        else:
            user = UserController.get_user_by_username(payload.get('claims').get('username'))
            AuthController.invalidate_jwt_token((auth.replace('Bearer ', '')))
            UserAuthLogController.log(user=user, action=UserAuthLogAction.LOGOUT)
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
                return jwt.decode(jwt=token, key=user.jwt_secret, audience=user.jwt_aud, algorithms='HS256')
            else:
                AuthController.invalidate_jwt_token(token=token)
                return False
            
        except Exception as e:
            AuthController.invalidate_jwt_token(token=token)
            raise e

    @staticmethod
    def invalidate_jwt_token(token: str) -> None:
        from app.Controllers import BlacklistedTokenController, AuthController
        payload = AuthController.validate_jwt(token.replace('Bearer ', ''))
        if payload.get('jti') is None:
            pass
        blacklist_id = f"{payload.get('aud')}:{payload.get('jti')}"
        BlacklistedTokenController.blacklist_token(blacklist_id, payload.get('exp'))

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
