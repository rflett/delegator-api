import datetime
import jwt
import typing
import uuid
from app import DBSession
from app.Controllers.LogControllers import UserAuthLogController
from app.Models import User
from app.Models.Enums import UserAuthLogAction
from app.Models.RBAC import Role
from flask import Response, request
from sqlalchemy import exists


TOKEN_TTL_IN_MINUTES = 60
session = DBSession()


def _get_user_from_request(req: request) -> typing.Union[User, Response]:
    """
    Get the user object that is claimed in the JWT payload.

    :param req request: The Flask request

    :return: A User object if a user is found, or a Flask Response
    """
    from app.Controllers import UserController

    # get auth from request
    auth = req.headers.get('Authorization', None)
    payload = AuthController.validate_jwt(auth.replace('Bearer ', ''))

    # get user id
    if isinstance(payload, dict):
        user_id = payload.get('claims').get('user_id')
    else:
        return _unauthenticated()

    # get User object
    try:
        user = UserController.get_user_by_id(user_id)
        return user
    except Exception as e:
        return Response('No user found.', 400)


def _unauthenticated(message: str = "Invalid credentials.") -> Response:
    """
    Simple helper function for returning a 403 Response.

    :param message str: The message to return
    :return: Response 403 Forbidden
    """
    return Response(message, status=403)


def _generate_jwt_token(user: User) -> str:
    """ 
    Creates a JWT token containing a relevant payload for the {user}.
    The jti is a uniqie identifier for the token.
    The exp is the time after which the token is no longer valid.
    
    :param user User: The user to generate the token for.

    :return: The token as a string.
    """
    payload = user.claims()
    if payload is None:
        payload = {}
    return jwt.encode(
        payload={
            **payload,
            "jti": str(uuid.uuid4()),
            "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=TOKEN_TTL_IN_MINUTES)
        },
        key=user.jwt_secret(),
        algorithm='HS256'
    ).decode("utf-8")


class AuthController(object):
    """
    The AuthController manages functions regarding generating, decoding and validating
    JWT tokens, login/logout functionality, and validating Authorization headers.
    """
    @staticmethod
    def authorize_request(request: request, operation: str, resource: str) -> typing.Union[Response, User]:
        auth_user = _get_user_from_request(request)
        if isinstance(auth_user, Response):
            return auth_user
        else:
            if auth_user.can(operation, resource):
                return auth_user
            else:
                return Response(f"No permissions to {operation} {resource}", 403)

    @staticmethod
    def login(req: dict) -> Response:
        """ 
        Logic for logging a user in. It will validate the request params and then return
        a JWT token with the user details.
        
        :param req dict: The request data as a dict

        :return: Response
        """
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
                    'Authorization': f"Bearer {_generate_jwt_token(user)}"
                }
            )
        else:
            return Response(
                "Password incorrect.",
                status=403
            )

    @staticmethod
    def logout(headers: dict) -> Response:
        """
        Logic for logging a user out. Basically checks the headers,
        gets the user, and then invalidates the JWT token.

        :param headers dict: The request headers as a dict.

        :return: Response
        """
        from app.Controllers import AuthController, UserController
        from app.Controllers.LogControllers import UserAuthLogController

        auth = headers.get('Authorization', None)
        payload = AuthController.validate_jwt(auth.replace('Bearer ', ''))

        if payload is False:
            return _unauthenticated('Invalid token.')
        else:
            user = UserController.get_user_by_id(payload.get('claims').get('user_id'))
            AuthController.invalidate_jwt_token((auth.replace('Bearer ', '')))
            UserAuthLogController.log(user=user, action=UserAuthLogAction.LOGOUT)
            return Response('Logged out')

    @staticmethod
    def validate_jwt(token: str) -> typing.Union[bool, dict]:
        """ 
        Validates a JWT token. The token will be decoded without any secret keys, to ensure it is actually
        a JWT token. Once the decode is successfull the userid will be pulled out of the token and
        then checked against what is in the database. If the user object can be retrieved (and hence their orgs
        secret key), then try and decode the JWT again with the secret key. 
        If this works, then the token is good, and JWT payload.

        :param token str: The JWT token as a string.

        :return: JWT payload if decode was successful, or False.
        """
        from app.Controllers import BlacklistedTokenController
        try:
            suspect_jwt = jwt.decode(jwt=token, algorithms='HS256', verify=False)

            # check if aud:jti is blacklisted
            blacklist_id = f"{suspect_jwt.get('aud')}:{suspect_jwt.get('jti')}"
            if BlacklistedTokenController.is_token_blacklisted(blacklist_id):
                return False

            # check user_id exists, is valid
            user_id = suspect_jwt.get('claims').get('user_id')
            if user_id is not None:
                from app.Controllers import UserController
                user = UserController.get_user_by_id(user_id)
                return jwt.decode(jwt=token, key=user.jwt_secret(), audience=user.jwt_aud(), algorithms='HS256')
            else:
                AuthController.invalidate_jwt_token(token=token)
                return False
            
        except Exception as e:
            AuthController.invalidate_jwt_token(token=token)
            raise e

    @staticmethod
    def invalidate_jwt_token(token: str) -> None:
        """ 
        Blacklists a JWT token. This involves getting the audience and unique id (aud and jti)
        and putting them in the blacklisted tokens table.

        :param token str: The token to invalidate.
        """
        from app.Controllers import BlacklistedTokenController, AuthController
        payload = AuthController.validate_jwt(token.replace('Bearer ', ''))
        if payload.get('jti') is None:
            pass
        blacklist_id = f"{payload.get('aud')}:{payload.get('jti')}"
        BlacklistedTokenController.blacklist_token(blacklist_id, payload.get('exp'))

    @staticmethod
    def check_authorization_header(auth: str) -> typing.Union[bool, Response]:
        """ 
        Checks to make sure there is a JWT token in the Bearer token. Does not validate it. 
        
        :param auth str: The Authorization header from the request.

        :return: True if the token exists and is a JWT, or an unauthenticated response.
        """

        if auth is None:
            return _unauthenticated("Missing Authorization header.")
        elif not isinstance(auth, str):
            return _unauthenticated(f"Expected Authorization header type str got {type(auth)}.")

        try:
            token = auth.replace('Bearer ', '')
            jwt.decode(jwt=token, algorithms='HS256', verify=False)
        except Exception as e:
            return _unauthenticated("Invalid token.")

        return True

    @staticmethod
    def role_exists(role_name: str) -> User:
        """
        Checks to see if a role exists

        :param role_name str: The role name

        :return: True if the role exists or False
        """
        return session.query(exists().where(Role.id == role_name)).scalar()
