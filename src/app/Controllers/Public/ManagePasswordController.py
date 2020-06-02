from flask import request, current_app
from flask_restx import Namespace, fields

from app.Controllers.Base import RequestValidationController
from app.Extensions.Database import session_scope
from app.Extensions.Errors import ValidationError, ResourceNotFoundError
from app.Models import Email
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
        self.purge_expired_tokens()
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

        reset_link = user.generate_new_invite_()

        link = current_app.config["PUBLIC_WEB_URL"] + "/reset-password?token=" + reset_link.token

        email = Email(user.email)
        email.send_password_reset(user.first_name, link)

        return "", 204

    request = api.model(
        "Password setup request", {"password": fields.String(required=True), "token": fields.String(required=True)}
    )
    response = api.model("Password setup response", {"email": fields.String()})

    @api.expect(request, validate=True)
    @api.marshal_with(response, code=200)
    def post(self):
        """Config a password after user creation or password reset"""
        request_body = request.get_json()

        # expire old and validate
        self.purge_expired_tokens()

        password_token = self.validate_password_token(request_body["token"])
        password = self.validate_password(request_body["password"])

        # set password
        user = user_service.get_by_id(password_token.user_id)

        # only reset if the password hasn't been set (or has been reset)
        with session_scope() as session:
            user.set_password(password)
            session.delete(password_token)

        return {"email": user.email}, 200
