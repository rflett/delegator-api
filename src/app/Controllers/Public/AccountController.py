import datetime
import json
import uuid
from os import getenv

import jwt
import requests
from flask import request, current_app
from flask_restx import Namespace, fields
from sqlalchemy import func, exists

from app.Controllers.Base import RequestValidationController
from app.Decorators import requires_jwt
from app.Extensions.Database import session_scope
from app.Extensions.Errors import AuthenticationError, ValidationError
from app.Models import Activity, Email
from app.Models.Dao import User, Organisation, TaskTemplate, FailedLogin
from app.Models.Enums import Events, Operations, Resources
from app.Services import UserService

api = Namespace(path="/account", name="Account", description="Manage an account")

user_service = UserService()


@api.route("/")
class AccountController(RequestValidationController):

    signup_request = api.model(
        "Signup Request",
        {
            "org_name": fields.String(required=True),
            "email": fields.String(required=True),
            "password": fields.String(required=True),
            "first_name": fields.String(required=True),
            "last_name": fields.String(required=True),
            "plan_id": fields.String(required=True, enum=["basic"]),
        },
    )
    signup_response = api.model("Signup Response", {"url": fields.String()})

    @api.expect(signup_request, validate=True)
    @api.marshal_with(signup_response, code=200)
    def put(self):
        """Signup a user."""
        request_body = request.get_json()

        with session_scope() as session:
            if session.query(
                exists().where(func.lower(Organisation.name) == func.lower(request_body["org_name"]))
            ).scalar():
                raise ValidationError("That organisation already exists.")
            if session.query(exists().where(func.lower(User.email) == func.lower(request_body["email"]))).scalar():
                raise ValidationError("That email already exists.")

        self.validate_email(request_body["email"])
        self.validate_password(request_body["password"])

        # create organisation
        try:
            with session_scope() as session:
                organisation = Organisation(
                    name=request_body["org_name"], chargebee_signup_plan=request_body["plan_id"]
                )
                session.add(organisation)

            with session_scope() as session:
                session.add(TaskTemplate(title="Other", org_id=organisation.id))

            organisation.create_settings()

        except Exception as e:
            # rollback
            current_app.logger.error(str(e))
            return "Hmm, we couldn't sign you up! Please contact support@delegator.com.au", 500

        # create user
        with session_scope() as session:
            user = User(
                org_id=organisation.id,
                email=request_body["email"],
                first_name=request_body["first_name"],
                last_name=request_body["last_name"],
                password=request_body["password"],
                role=current_app.config["SIGNUP_ROLE"],
            )
            session.add(user)

        user.create_settings()
        user.log(Operations.CREATE, Resources.USER, resource_id=user.id)
        current_app.logger.info(f"User {user.id} signed up.")

        # send email
        email = Email(user.email)
        email.send_welcome(user.first_name)

        # local mocking
        if getenv("MOCK_SERVICES"):
            with session_scope():
                organisation.chargebee_customer_id = "mock_customer_id"
                organisation.chargebee_subscription_id = "mock_customer_id"
                return {"url": "https://app.delegator.com.au/login"}, 200

        try:
            r = requests.post(
                url=f"{current_app.config['SUBSCRIPTION_API_PUBLIC_URL']}/customer/",
                headers={"Content-Type": "application/json", "Authorization": self.create_service_account_jwt()},
                data=json.dumps(
                    {
                        "plan_id": request_body["plan_id"],
                        "user": {"email": user.email, "first_name": user.first_name, "last_name": user.last_name},
                    }
                ),
                timeout=10,
            )
            if r.status_code != 200:
                current_app.logger.error(str(r.content))
                return "Hmm, we couldn't sign you up! Please contact support@delegator.com.au", 500

        except requests.exceptions.RequestException as e:
            current_app.logger.error(str(e))
            return "Hmm, we couldn't sign you up! Please contact support@delegator.com.au", 500

        response = r.json()
        with session_scope():
            organisation.chargebee_customer_id = response["customer_id"]
            organisation.chargebee_subscription_id = response["customer_id"]

        return {"url": response["url"]}, 200

    login_request = api.model(
        "Login Request", {"email": fields.String(required=True), "password": fields.String(required=True)}
    )
    login_response = api.model(
        "Login Response",
        {
            "id": fields.Integer(min=1),
            "uuid": fields.String(),
            "jwt": fields.String(),
            "first_name": fields.String(),
            "last_name": fields.String(),
            "job_title": fields.String(),
            "role": fields.String(enum=["ORG_ADMIN", "DELEGATOR", "USER", "LOCKED"]),
            "url": fields.String(),
        },
    )

    @api.expect(login_request, validate=True)
    @api.marshal_with(login_response, code=200)
    def post(self):
        """Log a user in."""
        request_body = request.get_json()

        email = request_body["email"]
        password = request_body["password"]
        self.validate_email(email)
        self.validate_password(password)

        with session_scope() as session:
            user: User = session.query(User).filter_by(email=email).first()

            if user is None:
                self._failed_login_attempt(email)
            else:
                user.clear_failed_logins()

            # check that the org is setup
            if not user.orgs.chargebee_setup_complete:
                # check with the subscription api to see if it has been completed
                customer_id = user.orgs.chargebee_customer_id
                try:
                    r = requests.get(
                        url=f"{self.url}/subscription/{customer_id}",
                        headers={"Authorization": f"Bearer {self.create_service_account_jwt()}"},
                        timeout=10,
                    )
                    if r.status_code != 200:
                        current_app.logger.error(str(r.content))
                        return "Hmm, we couldn't log you in! Please contact support@delegator.com.au", 500
                    subscription_id = r.json()["id"]
                except requests.exceptions.RequestException as e:
                    current_app.logger.error(str(e))
                    return "Hmm, we couldn't log you in! Please contact support@delegator.com.au", 500

                if not subscription_id == customer_id:
                    # redirect to setup chargebee stuff
                    try:
                        r = requests.post(
                            url=f"{self.url}/subscription/checkout/",
                            headers={
                                "Content-Type": "application/json",
                                "Authorization": f"Bearer {self.create_service_account_jwt()}",
                            },
                            data=json.dumps({"customer_id": customer_id, "plan_id": user.orgs.chargebee_signup_plan}),
                            timeout=10,
                        )
                        if r.status_code != 200:
                            current_app.logger.error(str(r.content))
                            return "Hmm, we couldn't log you in! Please contact support@delegator.com.au", 500
                        url = r.json()["url"]
                        return {"url": url}, 200
                    except requests.exceptions.RequestException as e:
                        current_app.logger.error(str(e))
                        return "Hmm, we couldn't log you in! Please contact support@delegator.com.au", 500

                else:
                    # the setup has been complete, and the webhook probably hasn't occurred fast enough
                    org = session.query(Organisation).filter_by(id=user.orgs.id).first()
                    org.chargebee_setup_complete = True

            # don't let them log in if they are disabled
            if user.disabled is not None:
                current_app.logger.info(f"Disabled user {user.id} tried to log in.")
                raise AuthenticationError(
                    "Cannot log in since this account has been disabled. Please consult your "
                    "Administrator for assistance."
                )

            # don't let them log in if they are deleted (unlikely to happen)
            if user.deleted is not None:
                current_app.logger.warning(f"Deleted user {user.id} tried to log in.")
                raise AuthenticationError(f"Email or password incorrect")

            # check login attempts
            if user.failed_login_attempts > 0:
                current_app.logger.info(
                    f"User {user.id} has failed to log in "
                    f"{user.failed_login_attempts} / {current_app.config['FAILED_LOGIN_ATTEMPTS_MAX']} times."
                )
                if user.failed_login_attempts >= current_app.config["FAILED_LOGIN_ATTEMPTS_MAX"]:
                    # check timeout
                    diff = (datetime.datetime.utcnow() - user.failed_login_time).seconds
                    if diff < current_app.config["FAILED_LOGIN_ATTEMPTS_TIMEOUT"]:
                        current_app.logger.info(
                            f"user last failed {diff}s ago. "
                            f"timeout is {current_app.config['FAILED_LOGIN_ATTEMPTS_TIMEOUT']}s"
                        )
                        raise AuthenticationError("Too many incorrect password attempts.")
                    else:
                        with session_scope():
                            # reset timeout
                            current_app.logger.info(
                                f"User last failed {diff}s ago. "
                                f"timeout is {current_app.config['FAILED_LOGIN_ATTEMPTS_TIMEOUT']}s."
                            )
                            user.failed_login_attempts = 0
                            user.failed_login_time = None

            # check password
            if user.password_correct(password):
                # reset failed attempts
                user.failed_login_attempts = 0
                user.failed_login_time = None
                user.is_active()
                Activity(
                    org_id=user.org_id, event=Events.user_login, event_id=user.id, event_friendly="Logged in."
                ).publish()

                # return the user dict and their JWT token
                return {**user.as_dict(), **{"jwt": self._generate_jwt_token(user)}}, 200
            else:
                current_app.logger.info(f"Incorrect password attempt for user {user.id}.")
                user.failed_login_attempts += 1
                user.failed_login_time = datetime.datetime.utcnow()
                raise AuthenticationError("Password incorrect.")

    @requires_jwt
    @api.response(204, "Success")
    def delete(self, **kwargs):
        """Log a user out"""
        req_user = kwargs["req_user"]
        req_user.is_inactive()
        Activity(
            org_id=req_user.org_id, event=Events.user_logout, event_id=req_user.id, event_friendly="Logged out."
        ).publish()
        current_app.logger.info(f"user {req_user.id} logged out")
        return "Successfully logged out", 204

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
                if failed_email.failed_attempts >= current_app.config["FAILED_LOGIN_ATTEMPTS_MAX"]:
                    # check timeout
                    diff = (datetime.datetime.utcnow() - failed_email.failed_time).seconds
                    if diff < current_app.config["FAILED_LOGIN_ATTEMPTS_TIMEOUT"]:
                        current_app.logger.info(
                            f"Email last failed {diff}s ago. "
                            f"Timeout is {current_app.config['FAILED_LOGIN_ATTEMPTS_TIMEOUT']}s"
                        )
                        raise AuthenticationError("Too many incorrect attempts.")
                    else:
                        # reset
                        current_app.logger.info(
                            f"Email last failed {diff}s ago. "
                            f"Timeout is {current_app.config['FAILED_LOGIN_ATTEMPTS_TIMEOUT']}s, resetting timeout."
                        )
                        session.delete(failed_email)
                        raise AuthenticationError("Email incorrect.")
                else:
                    # increment failed attempts
                    failed_email.failed_attempts += 1
                    failed_email.failed_time = datetime.datetime.utcnow()
                    current_app.logger.info(
                        f"Incorrect email attempt for user, " f"total failed attempts: {failed_email.failed_attempts}"
                    )
                    raise AuthenticationError("Email incorrect.")
            else:
                # hasn't failed before, so create it
                current_app.logger.info("User failed to log in.")
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
                "exp": datetime.datetime.utcnow()
                + datetime.timedelta(minutes=current_app.config["TOKEN_TTL_IN_MINUTES"]),
            },
            key=current_app.config["JWT_SECRET"],
            algorithm="HS256",
        ).decode("utf-8")
