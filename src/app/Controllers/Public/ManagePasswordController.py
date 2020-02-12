import datetime

from flask import request, current_app
from flask_restx import Namespace, fields

from app.Controllers.Base import RequestValidationController
from app.Extensions.Database import session_scope
from app.Extensions.Errors import ValidationError, ResourceNotFoundError
from app.Models import UserPasswordToken, Email
from app.Services import UserService

user_service = UserService()

api = Namespace(path="/password", name="Password Management", description="Manage passwords")


@api.route("/validate")
class ValidateToken(RequestValidationController):

    request = api.model("Validate Password Token Request", {"token": fields.String(required=True)})

    @api.expect(request, validate=True)
    @api.response(204, "Valid")
    def post(self, **kwargs):
        """Validates the token is valid and hasn't expired"""
        self._purge_expired_tokens()
        self.validate_password_token(request.get_json()["token"])
        return "", 204


@api.route("/")
class PasswordSetup(RequestValidationController):
    @api.param("email", "Email address of the user requesting a password reset.")
    @api.response(204, "Email with link to reset password has been sent.")
    def delete(self, **kwargs):
        """Request a password reset"""
        try:
            user_email = request.args["email"]
        except KeyError as e:
            raise ValidationError(f"Missing {e} from query params")

        try:
            self.validate_email(user_email)
            user = user_service.get_by_email(user_email)
            current_app.logger.info(f"User {user.name()} requested password reset.")
        except (ValidationError, ResourceNotFoundError):
            return "", 204

        with session_scope() as session:
            # delete old link if there's one
            session.query(UserPasswordToken).filter_by(user_id=user.id).delete()
            # create new link
            reset_link = UserPasswordToken(user.id)
            session.add(reset_link)

        link = current_app.config["PUBLIC_WEB_URL"] + "/reset-password?token=" + reset_link.token

        email = Email(user)
        email.send_password_reset(link)

        return "", 204

    request = api.model(
        "Password setup request", {"password": fields.String(required=True), "token": fields.String(required=True)}
    )
    response = api.model("Password setup response", {"email": fields.String()})

    @api.expect(request, validate=True)
    @api.marshal_with(response, 200)
    def post(self):
        """Config a password after user creation or password reset"""
        request_body = request.get_json()

        # expire old and validate
        self._purge_expired_tokens()

        password_token = self.validate_password_token(request_body["token"])
        password = self.validate_password(request_body["password"])

        # set password
        user = user_service.get_by_id(password_token.user_id)

        # only reset if the password hasn't been set (or has been reset)
        with session_scope() as session:
            user.set_password(password)
            session.delete(password_token)

        return {"email": user.email}, 200

    @staticmethod
    def _purge_expired_tokens() -> None:
        """Removes password tokens that have expired."""
        with session_scope() as session:
            now = int(datetime.datetime.utcnow().timestamp())
            delete_expired = (
                session.query(UserPasswordToken)
                .filter((UserPasswordToken.expire_after + UserPasswordToken.created_at) < now)
                .delete()
            )
            if delete_expired > 0:
                current_app.logger.info(f"Purged {delete_expired} password tokens which expired.")
