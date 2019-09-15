import datetime
import uuid

import jwt
from flask import Response, request

from app import logger, app, session_scope
from app.Controllers.Base import RequestValidationController
from app.Exceptions import AuthenticationError
from app.Models import User, FailedLogin, Activity
from app.Models.Enums import Events
from app.Services import UserService, TokenService


class AuthenticationController(RequestValidationController):
    user_service: UserService
    token_service: TokenService

    def __init__(self):
        RequestValidationController.__init__(self)
        self.user_service = UserService()
        self.token_service = TokenService()

    @staticmethod
    def _failed_login_attempt(email: str):
        """
        Checks to see if the email passed has failed to log in before due to it not existing. If this is the case
        it will update the failed logins table and increment the attempts and time. Checks are done against
        login limits to prevent excessive attempts to find email addresses.

        :param email:   The email that failed to login
        :return:        HTTP 401 response
        """
        with session_scope() as session:
            # check if it's failed before
            failed_email = session.query(FailedLogin).filter_by(email=email).first()
            if failed_email is not None:
                # check if it has breached the limits
                if failed_email.failed_attempts >= app.config['FAILED_LOGIN_ATTEMPTS_MAX']:
                    # check timeout
                    diff = (datetime.datetime.utcnow() - failed_email.failed_time).seconds
                    if diff < app.config['FAILED_LOGIN_ATTEMPTS_TIMEOUT']:
                        logger.info(f"Email last failed {diff}s ago. "
                                    f"Timeout is {app.config['FAILED_LOGIN_ATTEMPTS_TIMEOUT']}s")
                        raise AuthenticationError("Too many incorrect attempts.")
                    else:
                        # reset
                        logger.info(f"Email last failed {diff}s ago. "
                                    f"Timeout is {app.config['FAILED_LOGIN_ATTEMPTS_TIMEOUT']}s, resetting timeout.")
                        session.delete(failed_email)
                        raise AuthenticationError("Email incorrect.")
                else:
                    # increment failed attempts
                    failed_email.failed_attempts += 1
                    failed_email.failed_time = datetime.datetime.utcnow()
                    logger.info(f"Incorrect email attempt for user, "
                                f"total failed attempts: {failed_email.failed_attempts}")
                    raise AuthenticationError("Email incorrect.")
            else:
                # hasn't failed before, so create it
                logger.info("User failed to log in.")
                new_failure = FailedLogin(email=email)
                session.add(new_failure)
                raise AuthenticationError("Email incorrect.")

    @staticmethod
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

    def _validate_jwt(self, token: str) -> dict:
        """
        Validates a JWT token. The token will be decoded without any secret keys, to ensure it is actually
        a JWT token. Once the decode is successful the user_id will be pulled out of the token so that their org's
        JWT secret. This secret is then used to verify the JWT.

        :param token:   The JWT token as a string
        :return:        JWT payload if decode was successful
        """
        try:
            # decode the token without verifying against the org key
            suspect_jwt = jwt.decode(jwt=token, algorithms='HS256', verify=False)

            # check if aud:jti is blacklisted
            blacklist_id = suspect_jwt['aud'] + ':' + suspect_jwt['jti']
            if self.token_service.is_token_blacklisted(blacklist_id):
                raise AuthenticationError("JWT token has been blacklisted.")

            # get user_id from claims
            try:
                user_id = suspect_jwt['claims']['user_id']
                user = self.user_service.get_by_id(user_id)
                return jwt.decode(jwt=token, key=user.orgs.jwt_secret, audience=user.orgs.jwt_aud, algorithms='HS256')
            except KeyError:
                self._blacklist_token(token)
                raise AuthenticationError("JWT token has been blacklisted.")

        except Exception as e:
            logger.error(str(e))
            logger.info(f"Decoding raised {e}, we probably failed to decode the JWT due to a user secret/aud issue.")
            self._blacklist_token(token)
            raise AuthenticationError("JWT token has been blacklisted.")

    def _blacklist_token(self, token: str) -> None:
        """
        Blacklists a JWT token. This involves getting the audience and unique id (aud and jti)
        and putting them in the blacklisted tokens table.

        :param token: The token to invalidate.
        """
        payload = jwt.decode(jwt=token, algorithms='HS256', verify=False)
        blacklist_id = payload['aud'] + ':' + payload['jti']
        self.token_service.blacklist_token(blacklist_id, payload['exp'])

    def get_user_from_request(self) -> User:
        """Get the user object that is claimed in the JWT payload."""
        # get auth from request
        auth = request.headers.get('Authorization', None)

        payload = self._validate_jwt(auth.replace('Bearer ', ''))

        # get user
        try:
            return self.user_service.get_by_id(payload['claims']['user_id'])
        except (TypeError, KeyError) as e:
            logger.error(str(e))
            raise AuthenticationError("Unable to obtain user from the request.")

    def login(self) -> Response:
        """Log a user in."""
        # get params from http request
        request_body = request.get_json()
        email = request_body.get('email')
        password = request_body.get('password')

        # validate email
        self.validate_email(email)

        # validate password
        self.validate_password(password)

        with session_scope() as session:
            user = session.query(User).filter_by(email=email).first()

            if user is None:
                self._failed_login_attempt(email)
            else:
                user.clear_failed_logins()

            # don't let them log in if they are disabled
            if user.disabled is not None:
                logger.info(f"Disabled user {user.id} tried to log in.")
                raise AuthenticationError("Cannot log in since this account has been disabled. Please consult your "
                                          "Administrator for assistance.")

            # don't let them log in if they are deleted (unlikely to happen)
            if user.deleted is not None:
                logger.warning(f"Deleted user {user.id} tried to log in.")
                raise AuthenticationError(f"Email or password incorrect")

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
                        raise AuthenticationError("Too many incorrect password attempts.")
                    else:
                        with session_scope():
                            # reset timeout
                            logger.info(f"User last failed {diff}s ago. "
                                        f"timeout is {app.config['FAILED_LOGIN_ATTEMPTS_TIMEOUT']}s.")
                            user.failed_login_attempts = 0
                            user.failed_login_time = None

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
                return self.ok({
                    **user.fat_dict(),
                    **{"jwt": self._generate_jwt_token(user)}
                })
            else:
                logger.info(f"Incorrect password attempt for user {user.id}.")
                user.failed_login_attempts += 1
                user.failed_login_time = datetime.datetime.utcnow()
                raise AuthenticationError("Password incorrect.")

    @staticmethod
    def logout(self, **kwargs) -> Response:
        """Log a user out."""
        req_user = kwargs['req_user']

        auth = request.headers.get('Authorization', None)
        payload = self._validate_jwt(auth.replace('Bearer ', ''))

        if payload is False:
            raise AuthenticationError('Invalid token.')
        else:
            req_user.is_inactive()
            Activity(
                org_id=req_user.org_id,
                event=Events.user_logout,
                event_id=req_user.id,
                event_friendly="Logged out."
            ).publish()
            self._blacklist_token(auth.replace('Bearer ', ''))
            logger.info(f"user {req_user.id} logged out")
            return self.ok('Logged out')
