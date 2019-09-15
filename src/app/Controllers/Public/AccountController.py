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
from app.Decorators import handle_exceptions
from app.Exceptions import AuthenticationError
from app.Models import User, Activity, Organisation, TaskType
from app.Models.Enums import Events
from app.Models.Request import login_dto
from app.Models.Response import login_response_dto, message_response_dto

account_route = Namespace("Account", "Contains routes for logging in and registering", "/account")


@account_route.route("/")
class AccountController(RequestValidationController):
    @account_route.response(200, "Login Successful", login_response_dto)
    @account_route.response(400, "Login Failed", message_response_dto)
    @account_route.expect(login_dto)
    @handle_exceptions
    def post(self) -> Response:
        """Log a user in."""
        # get params from http request
        login_data = self.get_body()

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

    @account_route.response(200, "Registration Successful", message_response_dto)
    @account_route.response(400, "Registration Failed", message_response_dto)
    @handle_exceptions
    def put(self) -> Response:
        """Signup a user."""
        from app.Controllers import UserController

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
                organisation = Organisation(
                    name=org_name
                )
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
            user = UserController.create_signup_user(org_id=organisation.id, valid_user=valid_user)
        except Exception as e:
            logger.error(str(e))
            # the org was actually created, but the user failed, so delete the org and default task type
            with session_scope() as session:
                session.query(TaskType).filter_by(org_id=organisation.id).delete()
                session.delete(organisation)
                logger.info(f"Deleted the new organisation {organisation.name} "
                            f"since there was an issue creating the user.")
            return self.oh_god("There was an issue creating the user.")

        customer_id, plan_url = subscription_api.create_customer(
            plan_id=request_body.get('plan_id'),
            user_dict=user.as_dict(),
            org_name=organisation.name
        )

        with session_scope():
            organisation.chargebee_customer_id = customer_id

        return self.ok({"url": plan_url})

    @account_route.response(200, "Reset Password Successful", message_response_dto)
    @account_route.response(400, "Registration Failed", message_response_dto)
    @handle_exceptions
    def patch(self) -> Response:
        from app.Controllers import UserController
        request_body = request.get_json()
        self.validate_email(request_body.get('email'))

        with session_scope():
            logger.info(f"received password reset for {request_body.get('email')}")
            user = UserController.get_user_by_email(request_body.get('email'))
            new_password = ''.join([random.choice(string.ascii_letters + string.digits) for n in range(16)])
            user.reset_password(new_password)
            logger.info(json.dumps(user.as_dict()))
            logger.info(f"password successfully reset for {request_body.get('email')}")
            return self.ok(f"Password reset successfully, new password is {new_password}")

    def get_body(self) -> typing.Dict:
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
