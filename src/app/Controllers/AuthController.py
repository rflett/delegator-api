import datetime
import json
import jwt
import random
import string
import typing
import uuid
from app import logger, app, g_response, session_scope
from app.Controllers import ValidationController
from app.Controllers.LogControllers import UserAuthLogController
from app.Models import User, FailedLogin, Notification
from app.Models.Enums import UserAuthLogAction, Events
from app.Models.RBAC import Role, ResourceScope
from flask import Response, request
from sqlalchemy import exists


def _get_user_from_request(request_headers: dict) -> typing.Union[User, Response]:
    """
    Get the user object that is claimed in the JWT payload.
    :param request_headers: The Flask request headers
    :return:                A User object if a user is found, or a Flask Response
    """
    from app.Controllers import UserController

    # get auth from request
    auth = request_headers.get('Authorization', None)
    payload = AuthController.validate_jwt(auth.replace('Bearer ', ''))

    # get user id
    if isinstance(payload, dict):
        user_id = payload.get('claims').get('user_id')
        logger.debug(f"found user id {user_id} in the request JWT")
    else:
        logger.warning("missing payload from the bearer token")
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
        logger.debug("user claims is empty")
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


def _failed_login_attempt(email: str) -> Response:
    """
    Checks to see if the email passed has failed to log in before due to it not existing. If this is the case
    it will update the failed logins table and increment the attempts and time. Checks are done against
    login limits to prevent excessive attempts to find email addresses.
    :param email:   The email that failed to login
    :return:        A Flask Response
    """
    # check if it's failed before
    logger.info(f"attempted to login with non existing email {email}")
    with session_scope() as session:
        failed_email = session.query(FailedLogin).filter(FailedLogin.email == email).first()

    if failed_email is not None:
        # it's failed before so increment
        logger.info(f"email {email} has failed to log in "
                    f"{failed_email.failed_attempts} / {app.config['FAILED_LOGIN_ATTEMPTS_MAX']} times.")

        with session_scope() as session:
            # check if it has breached the limits
            if failed_email.failed_attempts >= app.config['FAILED_LOGIN_ATTEMPTS_MAX']:
                # check timeout
                diff = (datetime.datetime.utcnow() - failed_email.failed_time).seconds
                if diff < app.config['FAILED_LOGIN_ATTEMPTS_TIMEOUT']:
                    logger.info(f"email last failed {diff}s ago. "
                                f"timeout is {app.config['FAILED_LOGIN_ATTEMPTS_TIMEOUT']}s")
                    return g_response("Too many incorrect attempts.", 401)
                else:
                    # reset
                    logger.info(f"email last failed {diff}s ago. "
                                f"timeout is {app.config['FAILED_LOGIN_ATTEMPTS_TIMEOUT']}s. resetting timeout.")
                    session.delete(failed_email)
                    return g_response("Email incorrect.", 401)
            else:
                # increment
                failed_email.failed_attempts += 1
                failed_email.failed_time = datetime.datetime.utcnow()
                logger.info(f"incorrect email attempt for user {email}, "
                            f"total failed attempts: {failed_email.failed_attempts}")
                return g_response("Email incorrect.", 401)
    else:
        with session_scope() as session:
            # hasn't failed before, so create it
            logger.info(f"first login failure for email {email}")
            new_failure = FailedLogin(email=email)
            session.add(new_failure)
        return g_response("Email incorrect.", 401)


def _authorize_self(
        auth_user: User,
        user_permission_scope: str,
        operation: str,
        resource: str,
        resource_user_id: int,
        resource_org_id: int
) -> typing.Union[User, Response]:
    """ This user can only perform actions on resources it owns """
    if resource_user_id is not None and resource_org_id is not None:
        # check ids match
        if auth_user.id == resource_user_id and auth_user.org_id == resource_org_id:
            logger.info(f"user {auth_user.id} has {user_permission_scope} permissions, "
                        f"and can {operation} {resource}")
            return auth_user
        else:
            # they don't own this resource
            logger.info(f"No permissions to {operation} {resource}, "
                        f"because user {auth_user.id} != resource_user_id {resource_user_id} "
                        f"or user's org {auth_user.org_id} != resource_org_id {resource_org_id}")
            return g_response(f"No permissions to {operation} {resource}, "
                              f"because user {auth_user.id} does not own it.", 403)
    else:
        logger.warning(f"resource_org_id is None, resource_user_id is None")
        return g_response("resource_org_id is None, resource_user_id is None", 403)


def _authorize_org(
        auth_user: User,
        user_permission_scope: str,
        operation: str,
        resource: str,
        resource_user_id: int,
        resource_org_id: int
) -> typing.Union[User, Response]:
    """ this user can perform operations on resources in its organisation """
    from app.Controllers import UserController

    if resource_org_id is not None:
        # check org id matches
        if auth_user.org_id == resource_org_id:
            # optionally check resource_user_id is in same org
            if resource_user_id is not None:
                resource_user = UserController.get_user_by_id(resource_user_id)
                if auth_user.org_id != resource_user.org_id:
                    logger.info(f"No permissions to {operation} {resource}, "
                                f"because {auth_user.org_id} != {resource_user.org_id} "
                                f"however, {auth_user.org_id} == {resource_org_id}")
                    return g_response(f"No permissions to {operation} {resource}, "
                                      f"because user {auth_user.id} is not "
                                      f"in the same org as the resource user id {resource_user_id} which "
                                      f"is in org {resource_user.org_id}", 403)

            logger.info(f"user {auth_user.id} has {user_permission_scope} permissions, "
                        f"and can {operation} {resource}")
            return auth_user
        else:
            # this resource belongs to a different organisation
            logger.info(f"No permissions to {operation} {resource}, because "
                        f"user's org {auth_user.org_id} != resource_org_id {resource_org_id}")
            return g_response(f"No permissions to {operation} {resource}, "
                              f"because user {auth_user.id} is in org {auth_user.org_id} but "
                              f"the resource belongs to org {resource_org_id}.", 403)
    else:
        return g_response("resource_org_id is None", 403)


class AuthController(object):
    """
    The AuthController manages functions regarding generating, decoding and validating
    JWT tokens, login/logout functionality, and validating Authorization headers.
    """
    @staticmethod
    def authorize_request(
            request_headers: dict,
            operation: str,
            resource: str,
            resource_org_id: typing.Optional[int] = None,
            resource_user_id: typing.Optional[int] = None
    ) -> typing.Union[Response, User]:
        """
        Checks to see if the user in the request has authorization to perform the request operation on a
        particular resource.
        :param request_headers:     The request headers
        :param operation:           The operation to perform
        :param resource:            The resource to affect
        :param resource_org_id:     If the resource has an org_id, this is it
        :param resource_user_id:    If the resource has a user_id, this is it
        :return:                    The User object if they have authority, or a Response if the don't
        """
        # logger.info(f'authorizing request {json.dumps(request.get_json())}')
        auth_user = _get_user_from_request(request_headers)
        if isinstance(auth_user, Response):
            return auth_user
        else:
            # mark user as active
            auth_user.is_active()

            # deal with permissions
            user_permission_scope = auth_user.can(operation, resource)
            if user_permission_scope is False:
                logger.info(f"user id {auth_user.id} cannot perform {operation} on {resource}")
                return g_response(f"No permissions to {operation} {resource}", 403)

            elif user_permission_scope == ResourceScope.SELF:
                # this user can only perform actions on resources it owns
                return _authorize_self(
                    auth_user=auth_user,
                    user_permission_scope=user_permission_scope,
                    operation=operation,
                    resource=resource,
                    resource_user_id=resource_user_id,
                    resource_org_id=resource_org_id
                )

            elif user_permission_scope == ResourceScope.ORG:
                # this user can perform operations on resources in its organisation
                return _authorize_org(
                    auth_user=auth_user,
                    user_permission_scope=user_permission_scope,
                    operation=operation,
                    resource=resource,
                    resource_user_id=resource_user_id,
                    resource_org_id=resource_org_id
                )

            elif user_permission_scope == ResourceScope.GLOBAL:
                # admin OR scope doesn't apply for this permission since the check is done elsewhere
                logger.info(f"user {auth_user.id} has {user_permission_scope} permissions "
                            f"for {operation} {resource}")
                return auth_user

    @staticmethod
    def login(req: request) -> Response:
        """
        Logic for logging a user in. It will validate the request params and then return
        a JWT token with the user details.
        :param req: The request data as a dict
        :return:    Response
        """
        from app.Controllers import ValidationController, UserController
        request_body = req.get_json()
        email = request_body.get('email')
        password = request_body.get('password')
        logger.info(f"login requested for {email}")

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
            with session_scope() as session:
                user = session.merge(UserController.get_user_by_email(email))
                user.clear_failed_logins()
        else:
            # failed email attempt
            return _failed_login_attempt(email)

        # don't let them log in if they are disabled
        if user.disabled is True:
            logger.info(f"Disabled user {email} tried to log in.")
            return g_response(f"Cannot log in since this account has been disabled. Please consult your "
                              f"administrator for assistance.", 401)

        # don't let them log in if they are deleted (shouldn't happen but good to check)
        if user.deleted is True:
            logger.warning(f"Deleted user tried to log in.")
            return g_response(f"Email or password incorrect", 401)

        # check login attempts
        if user.failed_login_attempts > 0:
            logger.info(f"user {user.id} has failed to log in "
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
                        # reset
                        logger.info(f"user last failed {diff}s ago. "
                                    f"timeout is {app.config['FAILED_LOGIN_ATTEMPTS_TIMEOUT']}s. resetting timeout.")
                        user.failed_login_attempts = 0
                        user.failed_login_time = None

        with session_scope():
            # check password
            if user.password_correct(password):
                UserAuthLogController.log(
                    user=user,
                    action=UserAuthLogAction.LOGIN
                )
                logger.info(f"user {user.id} logged in")
                user.failed_login_attempts = 0
                user.failed_login_time = None
                user.is_active()
                Notification(
                    org_id=user.org_id,
                    event=Events.user_login,
                    payload=user.fat_dict()
                ).publish()
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
                logger.info(f"incorrect password attempt for user {user.id}")
                user.failed_login_attempts += 1
                user.failed_login_time = datetime.datetime.utcnow()
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
            user.is_inactive()
            Notification(
                org_id=user.org_id,
                event=Events.user_logout,
                payload=user.fat_dict()
            ).publish()
            AuthController.invalidate_jwt_token((auth.replace('Bearer ', '')))
            UserAuthLogController.log(user=user, action=UserAuthLogAction.LOGOUT)
            logger.info(f"user {user.id} logged out")
            return g_response('Logged out')

    @staticmethod
    def reset_password(req: request):
        from app.Controllers import UserController
        request_body = req.get_json()
        check_email = ValidationController.validate_email(request_body.get('email'))
        # invalid
        if isinstance(check_email, Response):
            return check_email

        with session_scope():
            logger.info(f"received password reset for {request_body.get('email')}")
            user = UserController.get_user_by_email(request_body.get('email'))
            new_password = ''.join([random.choice(string.ascii_letters + string.digits) for n in range(16)])
            user.reset_password(new_password)
            UserAuthLogController.log(user, 'reset_password')
            logger.info(json.dumps(user.as_dict()))
            logger.info(f"password successfully reset for {request_body.get('email')}")
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
                logger.info(f"user {suspect_jwt.get('claims').get('user_id')} does not exist")
                AuthController.invalidate_jwt_token(token=token)
                return False

        except Exception as e:
            logger.error(str(e))
            logger.info(f"decoding raised {e}, likely failed to decode jwt due to user secret/aud issue")
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
            logger.info(f"no jti in token")
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
            logger.info('missing authorization header')
            return g_response("Missing Authorization header.", 401)
        elif not isinstance(auth, str):
            logger.info(f"Expected Authorization header type str got {type(auth)}.")
            return g_response(f"Expected Authorization header type str got {type(auth)}.", 401)

        try:
            token = auth.replace('Bearer ', '')
            jwt.decode(jwt=token, algorithms='HS256', verify=False)
            return True
        except Exception as e:
            logger.error(str(e))
            return g_response("Invalid token.", 401)

    @staticmethod
    def role_exists(role_name: str) -> User:
        """ Checks to see if a role exists """
        with session_scope() as session:
            ret = session.query(exists().where(Role.id == role_name)).scalar()
            return ret
