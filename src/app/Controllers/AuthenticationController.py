import datetime
import json
import typing
import uuid

import jwt
from flask import Response, request

from app import logger, app, g_response, session_scope
from app.Exceptions import AuthenticationError
from app.Models import User, FailedLogin, Activity
from app.Models.Enums import Events


def _failed_login_attempt(email: str) -> Response:
    """
    Checks to see if the email passed has failed to log in before due to it not existing. If this is the case
    it will update the failed logins table and increment the attempts and time. Checks are done against
    login limits to prevent excessive attempts to find email addresses.

    :param email:   The email that failed to login
    :return:        HTTP 401 response
    """
    with session_scope() as session:
        # check if it's failed before
        failed_email = session.query(FailedLogin).filter(FailedLogin.email == email).first()
        if failed_email is not None:
            # check if it has breached the limits
            if failed_email.failed_attempts >= app.config['FAILED_LOGIN_ATTEMPTS_MAX']:
                # check timeout
                diff = (datetime.datetime.utcnow() - failed_email.failed_time).seconds
                if diff < app.config['FAILED_LOGIN_ATTEMPTS_TIMEOUT']:
                    logger.info(f"Email last failed {diff}s ago. "
                                f"Timeout is {app.config['FAILED_LOGIN_ATTEMPTS_TIMEOUT']}s")
                    return g_response("Too many incorrect attempts.", 401)
                else:
                    # reset
                    logger.info(f"Email last failed {diff}s ago. "
                                f"Timeout is {app.config['FAILED_LOGIN_ATTEMPTS_TIMEOUT']}s, resetting timeout.")
                    session.delete(failed_email)
                    return g_response("Email incorrect.", 401)
            else:
                # increment failed attempts
                failed_email.failed_attempts += 1
                failed_email.failed_time = datetime.datetime.utcnow()
                logger.info(f"Incorrect email attempt for user, "
                            f"total failed attempts: {failed_email.failed_attempts}")
                return g_response("Email incorrect.", 401)
        else:
            # hasn't failed before, so create it
            logger.info("User failed to log in.")
            new_failure = FailedLogin(email=email)
            session.add(new_failure)
            return g_response("Email incorrect.", 401)


def _generate_jwt_token(user: User) -> str:
    """
    Creates a JWT token containing a relevant payload for the user.
    The jti is a unique identifier for the token.
    The exp is the time after which the token is no longer valid.

    :param user:    The user to generate the token for
    :return:        The token as a string
    """
    payload = user.claims()
    if payload is None:
        payload = {}
    return jwt.encode(
        payload={
            **payload,
            "jti": str(uuid.uuid4()),
            "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=app.config['TOKEN_TTL_IN_MINUTES'])
        },
        key=user.orgs.jwt_secret,
        algorithm='HS256'
    ).decode("utf-8")


def _validate_jwt(token: str) -> dict:
    """
    Validates a JWT token. The token will be decoded without any secret keys, to ensure it is actually
    a JWT token. Once the decode is successful the user_id will be pulled out of the token so that their org's
    JWT secret. This secret is then used to verify the JWT.

    :param token:   The JWT token as a string
    :return:        JWT payload if decode was successful
    """
    from app.Controllers import BlacklistedTokenController, UserController
    try:
        # decode the token without verifying against the org key
        suspect_jwt = jwt.decode(jwt=token, algorithms='HS256', verify=False)

        # check if aud:jti is blacklisted
        blacklist_id = suspect_jwt['aud'] + ':' + suspect_jwt['jti']
        if BlacklistedTokenController.is_token_blacklisted(blacklist_id):
            raise AuthenticationError("JWT token has been blacklisted.")

        # get user_id from claims
        try:
            user_id = suspect_jwt['claims']['user_id']
            user = UserController.get_user_by_id(user_id)
            return jwt.decode(jwt=token, key=user.orgs.jwt_secret, audience=user.orgs.jwt_aud, algorithms='HS256')
        except KeyError:
            _blacklist_token(token)
            raise AuthenticationError("JWT token has been blacklisted.")

    except Exception as e:
        logger.error(str(e))
        logger.info(f"Decoding raised {e}, we probably failed to decode the JWT due to a user secret/aud issue.")
        _blacklist_token(token)
        raise AuthenticationError("JWT token has been blacklisted.")


def _blacklist_token(token: str) -> None:
    """
    Blacklists a JWT token. This involves getting the audience and unique id (aud and jti)
    and putting them in the blacklisted tokens table.

    :param token: The token to invalidate.
    """
    from app.Controllers import BlacklistedTokenController
    payload = jwt.decode(jwt=token, algorithms='HS256', verify=False)
    blacklist_id = payload['aud'] + ':' + payload['jti']
    BlacklistedTokenController.blacklist_token(blacklist_id, payload['exp'])


class AuthenticationController(object):
    @staticmethod
    def check_authorization_header(auth: str) -> typing.Union[bool, Response]:
        """
        Checks to make sure there is a JWT token in the Bearer token. Does not validate it.

        :param auth:    The Authorization header from the request.
        :return:        True if the token exists and is a JWT, or HTTP 401 Response
        """
        try:
            token = auth.replace('Bearer ', '')
            jwt.decode(jwt=token, algorithms='HS256', verify=False)
            return True
        except TypeError as e:
            logger.error(str(e))
            return g_response("Invalid Authorization header.", 401)

    @staticmethod
    def get_user_from_request(request_headers: dict) -> User:
        """
        Get the user object that is claimed in the JWT payload.

        :param request_headers: The HTTP request headers
        :return:                A User object if a user is found
        """
        from app.Controllers import UserController

        # get auth from request
        auth = request_headers.get('Authorization', None)

        payload = _validate_jwt(auth.replace('Bearer ', ''))

        # get user
        try:
            return UserController.get_user_by_id(payload['claims']['user_id'])
        except (TypeError, KeyError) as e:
            logger.error(str(e))
            raise AuthenticationError("Unable to obtain user from the request.")

    @staticmethod
    def login(req: request) -> Response:
        """ Log a user in.

        :param req: The HTTP request
        :return:    An HTTP 200 or 401 response
        """
        from app.Controllers import ValidationController, UserController

        # get params from http request
        request_body = req.get_json()
        email = request_body.get('email')
        password = request_body.get('password')

        # validate email
        ValidationController.validate_email(email)

        # validate password
        ValidationController.validate_password(password)

        # get user
        if UserController.user_exists(email):
            with session_scope() as session:
                user = session.merge(UserController.get_user_by_email(email))
                user.clear_failed_logins()
        else:
            # user doesn't exist so mark as a failed attempt against the email
            return _failed_login_attempt(email)

        # don't let them log in if they are disabled
        if user.disabled is not None:
            logger.info(f"Disabled user {user.id} tried to log in.")
            return g_response(f"Cannot log in since this account has been disabled. Please consult your "
                              f"Administrator for assistance.", 401)

        # don't let them log in if they are deleted (unlikely to happen)
        if user.deleted is not None:
            logger.warning(f"Deleted user {user.id} tried to log in.")
            return g_response(f"Email or password incorrect", 401)

        # check login attempts
        if user.failed_login_attempts > 0:
            logger.info(f"User {user.id} has failed to log in "
                        f"{user.failed_login_attempts} / {app.config['FAILED_LOGIN_ATTEMPTS_MAX']} times.")
            if user.failed_login_attempts >= app.config['FAILED_LOGIN_ATTEMPTS_MAX']:
                # check timeout
                diff = (datetime.datetime.utcnow() - user.failed_login_time).seconds
                if diff < app.config['FAILED_LOGIN_ATTEMPTS_TIMEOUT']:
                    logger.info(f"user last failed {diff}s ago. "
                                f"timeout is {app.config['FAILED_LOGIN_ATTEMPTS_TIMEOUT']}s")
                    return g_response("Too many incorrect password attempts.", 401)
                else:
                    with session_scope():
                        # reset timeout
                        logger.info(f"User last failed {diff}s ago. "
                                    f"timeout is {app.config['FAILED_LOGIN_ATTEMPTS_TIMEOUT']}s. Resetting timeout.")
                        user.failed_login_attempts = 0
                        user.failed_login_time = None

        with session_scope():
            # check password
            if user.password_correct(password):
                # reset failed attempts
                user.failed_login_attempts = 0
                user.failed_login_time = None
                user.is_active()
                Activity(
                    org_id=user.org_id,
                    event=Events.user_login,
                    event_id=user.id,
                    event_friendly="Logged in."
                ).publish()

                # return the user dict and their JWT token
                return Response(
                    json.dumps({
                        **user.fat_dict(),
                        **{"jwt": _generate_jwt_token(user)}
                    }),
                    status=200,
                    headers={
                        'Content-Type': 'application/json'
                    }
                )
            else:
                logger.info(f"Incorrect password attempt for user {user.id}.")
                user.failed_login_attempts += 1
                user.failed_login_time = datetime.datetime.utcnow()
                return g_response("Password incorrect.", 401)

    @staticmethod
    def logout(headers: dict) -> Response:
        """ Log a user out.

        :param headers: The HTTP request headers
        :return:        An HTTP 401 or 200 response
        """
        from app.Controllers import UserController

        auth = headers.get('Authorization', None)
        payload = _validate_jwt(auth.replace('Bearer ', ''))

        if payload is False:
            return g_response('Invalid token.', 401)
        else:
            user = UserController.get_user_by_id(payload.get('claims').get('user_id'))
            user.is_inactive()
            Activity(
                org_id=user.org_id,
                event=Events.user_logout,
                event_id=user.id,
                event_friendly="Logged out."
            ).publish()
            _blacklist_token(auth.replace('Bearer ', ''))
            logger.info(f"user {user.id} logged out")
            return g_response('Logged out')
