import datetime
import json
import jwt
import random
import string
import typing
import uuid
from app import session, logger, app, g_response
from app.Controllers import ValidationController
from app.Controllers.LogControllers import UserAuthLogController
from app.Models import User, LoginBadEmail
from app.Models.Enums import UserAuthLogAction
from app.Models.RBAC import Role
from flask import Response, request
from sqlalchemy import exists


def _get_user_from_request(req: request) -> typing.Union[User, Response]:
    """
    Get the user object that is claimed in the JWT payload.
    :param req: The Flask request
    :return:    A User object if a user is found, or a Flask Response
    """
    from app.Controllers import UserController

    # get auth from request
    auth = req.headers.get('Authorization', None)
    payload = AuthController.validate_jwt(auth.replace('Bearer ', ''))

    # get user id
    if isinstance(payload, dict):
        user_id = payload.get('claims').get('user_id')
        logger.debug(f"Got user ID {user_id}")
    else:
        return g_response("Missing payload from Bearer token", 401)

    # get User object
    try:
        user = UserController.get_user_by_id(user_id)
        return user
    except Exception as e:
        logger.error(str(e))
        return g_response('No user found in Bearer token.', 401)


def _generate_jwt_token(user: User) -> str:
    """
    Creates a JWT token containing a relevant payload for the {user}.
    The jti is a uniqie identifier for the token.
    The exp is the time after which the token is no longer valid.
    :param user:    The user to generate the token for.
    :return:        The token as a string.
    """
    payload = user.claims()
    if payload is None:
        logger.debug(f"Claims payload was None")
        payload = {}
    return jwt.encode(
        payload={
            **payload,
            "jti": str(uuid.uuid4()),
            "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=app.config['TOKEN_TTL_IN_MINUTES'])
        },
        key=user.jwt_secret(),
        algorithm='HS256'
    ).decode("utf-8")


def _clear_failed_logins(email: str) -> None:
    """
    Removes an email address from the failed logins table
    :param email:   The email to clear
    :return:        None
    """
    failed_email = session.query(exists().where(LoginBadEmail.email == email)).scalar()
    if failed_email:
        session.query(LoginBadEmail).filter(LoginBadEmail.email == email).delete()


def _failed_login_attempt(email: str) -> Response:
    """
    Checks to see if the email passed has failed to log in before due to it not existing. If this is the case
    it will update the failed logins table and increment the attempts and time. Checks are done against
    login limits to prevent excessive attempts to find email addresses.
    :param email:   The email that failed to login
    :return:        A Flask Response
    """
    # check if it's failed before
    logger.debug(f"attempted to login with non existing email {email}")
    failed_email = session.query(exists().where(LoginBadEmail.email == email)).scalar()
    if failed_email:
        # it's failed before so increment
        failure_entry = session.query(LoginBadEmail).filter(LoginBadEmail.email == email).first()
        logger.debug(f"email {email} has failed to log in "
                     f"{failure_entry.failed_attempts} / {app.config['FAILED_LOGIN_ATTEMPTS_MAX']} times.")
        # check if it has breached the limits
        if failure_entry.failed_attempts >= app.config['FAILED_LOGIN_ATTEMPTS_MAX']:
            # check timeout
            diff = (datetime.datetime.utcnow() - failure_entry.failed_time).seconds
            if diff < app.config['FAILED_LOGIN_ATTEMPTS_TIMEOUT']:
                logger.debug(f"email last failed {diff}s ago. "
                             f"timeout is {app.config['FAILED_LOGIN_ATTEMPTS_TIMEOUT']}s")
                return g_response("Too many incorrect attempts.", 401)
            else:
                # reset
                logger.debug(f"email last failed {diff}s ago. "
                             f"timeout is {app.config['FAILED_LOGIN_ATTEMPTS_TIMEOUT']}s. resetting timeout.")
                session.delete(failure_entry)
                return g_response("Email incorrect.", 401)
        else:
            # increment
            failure_entry.failed_attempts += 1
            failure_entry.failed_time = datetime.datetime.utcnow()
            session.commit()
            logger.debug(f"incorrect email attempt for user {email}")
            return g_response("Email incorrect.", 401)
    else:
        # hasn't failed before, so create it
        logger.debug(f"first login failure for email {email}")
        new_failure = LoginBadEmail(email=email)
        session.add(new_failure)
        session.commit()
        return g_response("Email incorrect.", 401)


class AuthController(object):
    """
    The AuthController manages functions regarding generating, decoding and validating
    JWT tokens, login/logout functionality, and validating Authorization headers.
    """
    @staticmethod
    def authorize_request(
            request: request,
            operation: str,
            resource: str
    ) -> typing.Union[Response, User]:
        """
        Checks to see if the user in the request has authorization to perform the request operation on a
        particular resource.
        :param request:     The request object
        :param operation:   The operation to perform
        :param resource:    The resource to affect
        :return:            The User object if they have authority, or a Response if the don't
        """
        logger.debug(f'authorizing request {json.dumps(request.get_json())}')
        auth_user = _get_user_from_request(request)
        if isinstance(auth_user, Response):
            return auth_user
        else:
            if auth_user.can(operation, resource):
                logger.debug(f"user id {auth_user.id} can perform {operation} on {resource}")
                return auth_user
            else:
                logger.debug(f"user id {auth_user.id} cannot perform {operation} on {resource}")
                return g_response(f"No permissions to {operation} {resource}", 403)

    @staticmethod
    def login(req: dict) -> Response:
        """
        Logic for logging a user in. It will validate the request params and then return
        a JWT token with the user details.
        :param req: The request data as a dict
        :return:    Response
        """
        from app.Controllers import ValidationController, UserController

        email = req.get('email')
        password = req.get('password')

        logger.debug(f"login requested for {json.dumps(req)}")

        # validate email
        email_validate_res = ValidationController.validate_email(email)
        if isinstance(email_validate_res, Response):
            return email_validate_res

        # validate password
        password_validate_res = ValidationController.validate_password(password)
        if isinstance(password_validate_res, Response):
            return password_validate_res

        # get user
        if UserController.user_exists(email):
            user = session.merge(UserController.get_user_by_email(email))
            _clear_failed_logins(user.email)
        else:
            # bad email attempt
            return _failed_login_attempt(email)

        # check login attempts
        if user.failed_login_attempts > 0:
            logger.debug(f"user {user.id} has failed to log in "
                         f"{user.failed_login_attempts} / {app.config['FAILED_LOGIN_ATTEMPTS_MAX']} times.")
            if user.failed_login_attempts >= app.config['FAILED_LOGIN_ATTEMPTS_MAX']:
                # check timeout
                diff = (datetime.datetime.utcnow() - user.failed_login_time).seconds
                if diff < app.config['FAILED_LOGIN_ATTEMPTS_TIMEOUT']:
                    logger.debug(f"user last failed {diff}s ago. "
                                 f"timeout is {app.config['FAILED_LOGIN_ATTEMPTS_TIMEOUT']}s")
                    return g_response("Too many incorrect password attempts.", 401)
                else:
                    # reset
                    logger.debug(f"user last failed {diff}s ago. "
                                 f"timeout is {app.config['FAILED_LOGIN_ATTEMPTS_TIMEOUT']}s. resetting timeout.")
                    user.failed_login_attempts = 0
                    user.failed_login_time = None
                    session.commit()

        # check password
        if user.check_password(password):
            UserAuthLogController.log(
                user=user,
                action=UserAuthLogAction.LOGIN
            )
            logger.debug(f"user {user.id} logged in")
            user.failed_login_attempts = 0
            user.failed_login_time = None
            session.commit()
            return g_response(
                "Welcome.",
                status=200,
                headers={
                    'Authorization': f"Bearer {_generate_jwt_token(user)}"
                }
            )
        else:
            logger.debug(f"incorrect password attempt for user {user.id}")
            user.failed_login_attempts += 1
            user.failed_login_time = datetime.datetime.utcnow()
            session.commit()
            return g_response("Password incorrect.", 401)

    @staticmethod
    def logout(headers: dict) -> Response:
        """
        Logic for logging a user out. Basically checks the headers,
        gets the user, and then invalidates the JWT token.
        :param headers: The request headers as a dict.
        :return:        Response
        """
        from app.Controllers import AuthController, UserController
        from app.Controllers.LogControllers import UserAuthLogController

        auth = headers.get('Authorization', None)
        payload = AuthController.validate_jwt(auth.replace('Bearer ', ''))

        if payload is False:
            return g_response('Invalid token.', 401)
        else:
            user = UserController.get_user_by_id(payload.get('claims').get('user_id'))
            AuthController.invalidate_jwt_token((auth.replace('Bearer ', '')))
            UserAuthLogController.log(user=user, action=UserAuthLogAction.LOGOUT)
            logger.debug(f"user {user.id} logged out")
            return g_response('Logged out')

    @staticmethod
    def reset_password(request_body: dict):
        from app.Controllers import UserController
        check_email = ValidationController.validate_email(request_body.get('email'))
        if isinstance(check_email, Response):
            return check_email
        else:
            logger.debug(f"received password reset for {request_body.get('email')}")
            user = UserController.get_user_by_email(request_body.get('email'))
            new_password = ''.join([random.choice(string.ascii_letters + string.digits) for n in range(16)])
            user.reset_password(new_password)
            UserAuthLogController.log(user, 'reset_password')
            session.commit()
            logger.debug(json.dumps(user.as_dict()))
            logger.debug(f"password successfully reset for {request_body.get('email')}")
            return g_response(f"Password reset successfully, new password is {new_password}")

    @staticmethod
    def validate_jwt(token: str) -> typing.Union[bool, dict]:
        """
        Validates a JWT token. The token will be decoded without any secret keys, to ensure it is actually
        a JWT token. Once the decode is successfull the userid will be pulled out of the token and
        then checked against what is in the database. If the user object can be retrieved (and hence their orgs
        secret key), then try and decode the JWT again with the secret key.
        If this works, then the token is good, and JWT payload.
        :param token:   The JWT token as a string.
        :return:        JWT payload if decode was successful, or False.
        """
        from app.Controllers import BlacklistedTokenController
        try:
            suspect_jwt = jwt.decode(jwt=token, algorithms='HS256', verify=False)
            logger.debug(f"received suspect jwt {suspect_jwt}")

            # check if aud:jti is blacklisted
            blacklist_id = f"{suspect_jwt.get('aud')}:{suspect_jwt.get('jti')}"
            if BlacklistedTokenController.is_token_blacklisted(blacklist_id):
                return False

            # check user_id exists, is valid
            user_id = suspect_jwt.get('claims').get('user_id')
            if user_id is not None:
                from app.Controllers import UserController
                user = UserController.get_user_by_id(user_id)
                logger.debug(f"found user {user.id} in jwt claim. attempting to decode jwt.")
                return jwt.decode(jwt=token, key=user.jwt_secret(), audience=user.jwt_aud(), algorithms='HS256')
            else:
                logger.debug(f"user {suspect_jwt.get('claims').get('user_id')} does not exist")
                AuthController.invalidate_jwt_token(token=token)
                return False

        except Exception as e:
            logger.error(str(e))
            logger.debug(f"decoding raised {e}, likely failed to decode jwt due to user secret/aud issue")
            AuthController.invalidate_jwt_token(token=token)

    @staticmethod
    def invalidate_jwt_token(token: str) -> None:
        """
        Blacklists a JWT token. This involves getting the audience and unique id (aud and jti)
        and putting them in the blacklisted tokens table.
        :param token: The token to invalidate.
        """
        from app.Controllers import BlacklistedTokenController
        payload = jwt.decode(jwt=token, algorithms='HS256', verify=False)
        if payload.get('jti') is None:
            logger.debug(f"no jti in token")
            pass
        blacklist_id = f"{payload.get('aud')}:{payload.get('jti')}"
        BlacklistedTokenController.blacklist_token(blacklist_id, payload.get('exp'))

    @staticmethod
    def check_authorization_header(auth: str) -> typing.Union[bool, Response]:
        """
        Checks to make sure there is a JWT token in the Bearer token. Does not validate it.
        :param auth:    The Authorization header from the request.
        :return:        True if the token exists and is a JWT, or an unauthenticated response.
        """

        if auth is None:
            logger.debug('missing authorization header')
            return g_response("Missing Authorization header.", 401)
        elif not isinstance(auth, str):
            logger.debug(f"Expected Authorization header type str got {type(auth)}.")
            return g_response(f"Expected Authorization header type str got {type(auth)}.", 401)

        try:
            token = auth.replace('Bearer ', '')
            jwt.decode(jwt=token, algorithms='HS256', verify=False)

        except Exception as e:
            logger.error(str(e))
            return g_response("Invalid token.", 401)

        return True

    @staticmethod
    def role_exists(role_name: str) -> User:
        """
        Checks to see if a role exists
        :param role_name:   The role name
        :return:            True if the role exists or False
        """
        return session.query(exists().where(Role.id == role_name)).scalar()
