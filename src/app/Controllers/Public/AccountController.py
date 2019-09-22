import datetime
import json
import random
import string
import typing
import uuid

import jwt
from flask import Response, request
from flask_restplus import Namespace

from app import app, session_scope, logger, subscription_api
from app.Controllers.Base import RequestValidationController
from app.Decorators import handle_exceptions, requires_jwt
from app.Exceptions import AuthenticationError
from app.Models import User, Activity, Organisation, TaskType, FailedLogin
from app.Models.Enums import Events, Operations, Resources
from app.Models.Request import login_request, signup_request
from app.Models.Response import login_response, message_response_dto, signup_response
from app.Services import UserService

account_route = Namespace(
    path="/account",
    name="Account",
    description="Contains routes for logging in and registering"
)

user_service = UserService()


@account_route.route("/")
class AccountController(RequestValidationController):

    @handle_exceptions
    @account_route.expect(signup_request)
    @account_route.response(200, "Registration Successful", signup_response)
    @account_route.response(400, "Registration Failed", message_response_dto)
    def put(self) -> Response:
        """Signup a user."""
        # get the request body
        request_body = request.get_json()

        # validate org
        org_name = self.validate_create_org_request(request_body)

        # validate user
        valid_user = self.validate_create_signup_user(request_body)

        # try and create the org, if there are issues then
        try:
            # create the organisation
            with session_scope() as session:
                organisation = Organisation(name=org_name)
                session.add(organisation)

            # add default task type
            with session_scope() as session:
                session.add(TaskType(label='Other', org_id=organisation.id))

            # create org settings
            organisation.create_settings()

        except Exception as e:
            logger.error(str(e))
            return self.oh_god("There was an issue creating the organisation.")

        # try and create the user since the org was created successfully
        try:
            with session_scope() as session:
                user = User(
                    org_id=organisation.id,
                    email=valid_user.get('email'),
                    first_name=valid_user.get('first_name'),
                    last_name=valid_user.get('last_name'),
                    password=valid_user.get('password'),
                    role=valid_user.get('role'),
                    job_title=valid_user.get('job_title')
                )
                session.add(user)

            with session_scope():
                user.created_by = user.id

            # create user settings
            user.create_settings()

            user.log(
                operation=Operations.CREATE,
                resource=Resources.USER,
                resource_id=user.id
            )
            # publish event
            Activity(
                org_id=user.org_id,
                event=Events.user_created,
                event_id=user.id,
                event_friendly=f"Created by {user.name()}"
            ).publish()
            logger.info(f"User {user.id} signed up.")

            customer_id, plan_url = subscription_api.create_customer(
                plan_id=request_body.get('plan_id'),
                user_dict=user.as_dict(),
                org_name=organisation.name
            )

            with session_scope():
                organisation.chargebee_customer_id = customer_id

            return self.ok({"url": plan_url})

        except Exception as e:
            logger.error(str(e))
            # the org was actually created, but the user failed, so delete the org and default task type
            with session_scope() as session:
                session.query(TaskType).filter_by(org_id=organisation.id).delete()
                session.delete(organisation)
                logger.info(f"Deleted the new organisation {organisation.name} "
                            f"since there was an issue creating the user.")
            return self.oh_god("There was an issue creating the user.")

    @handle_exceptions
    @account_route.expect(login_request)
    @account_route.response(200, "Login Successful", login_response)
    @account_route.response(400, "Login Failed", message_response_dto)
    def post(self) -> Response:
        """Log a user in."""
        # get params from http request
        login_data = self._get_login_body()

        with session_scope() as session:
            user: User = session.query(User).filter_by(email=login_data["email"]).first()

            if user is None:
                self._failed_login_attempt(login_data["email"])
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
            if user.password_correct(login_data["password"]):
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

    @handle_exceptions
    @account_route.response(200, "Reset Password Successful", message_response_dto)
    @account_route.response(400, "Registration Failed", message_response_dto)
    def patch(self) -> Response:
        """Reset a password in the world's worst way"""
        request_body = request.get_json()
        self.validate_email(request_body.get('email'))

        with session_scope():
            logger.info(f"received password reset for {request_body.get('email')}")
            user = user_service.get_by_email(request_body.get('email'))
            new_password = ''.join([random.choice(string.ascii_letters + string.digits) for n in range(16)])
            user.reset_password(new_password)
            logger.info(json.dumps(user.as_dict()))
            logger.info(f"password successfully reset for {request_body.get('email')}")
            return self.ok(f"Password reset successfully, new password is {new_password}")

    @handle_exceptions
    @requires_jwt
    @account_route.response(200, "Logout Successful")
    @account_route.response(400, "Logout Failed")
    def delete(self, **kwargs) -> Response:
        """Log a user out"""
        req_user = kwargs['req_user']
        req_user.is_inactive()
        Activity(
            org_id=req_user.org_id,
            event=Events.user_logout,
            event_id=req_user.id,
            event_friendly="Logged out."
        ).publish()
        logger.info(f"user {req_user.id} logged out")
        return self.ok('Successfully logged out')

    def _get_login_body(self) -> typing.Dict:
        """get params from http request"""
        request_body: dict = request.get_json()
        email = request_body.get('email')
        password = request_body.get('password')
        # validate email
        self.validate_email(email)
        # validate password
        self.validate_password(password)

        return {
            "email": email,
            "password": password
        }

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
            key=app.config['JWT_SECRET'],
            algorithm='HS256'
        ).decode("utf-8")
