import time

from flask import Response, request
from flask_restplus import Namespace

from app import session_scope, logger, email_api, app
from app.Controllers.Base import RequestValidationController
from app.Decorators import handle_exceptions
from app.Exceptions import ValidationError, ResourceNotFoundError
from app.Models import UserPasswordToken
from app.Models.Request import password_setup_request
from app.Models.Response import password_setup_response, message_response_dto
from app.Services import UserService

user_service = UserService()

password_setup_route = Namespace(
    path="/password",
    name="Password Management",
    description="Manage passwords"
)


@password_setup_route.route("/")
class PasswordSetup(RequestValidationController):

    @handle_exceptions
    @password_setup_route.param('token', 'The token that the user received to manage their password.')
    @password_setup_route.response(204, "The token is still valid.")
    @password_setup_route.response(400, "Bad Request", message_response_dto)
    def get(self):
        """Validates the token is valid and hasn't expired"""
        self._purge_expired_tokens()
        self.validate_password_link()
        return self.no_content()

    @handle_exceptions
    @password_setup_route.param('email', 'Email address of the user requesting a password reset.')
    @password_setup_route.response(204, "Email with link to reset password has been sent.")
    @password_setup_route.response(400, "Password Reset Request Failed", message_response_dto)
    def delete(self) -> Response:
        """Request a password reset"""
        try:
            email = request.args['email']
        except KeyError as e:
            raise ValidationError(f"Missing {e} from query params")

        try:
            self.validate_email(email)
            user = user_service.get_by_email(email)
            logger.info(f"User {user.name()} requested password reset.")
        except (ValidationError, ResourceNotFoundError):
            return self.no_content()

        with session_scope() as session:
            # delete old link if there's one
            session.query(UserPasswordToken).filter_by(user_id=user.id).delete()
            # create new link
            reset_link = UserPasswordToken(user.id)
            session.add(reset_link)

        link = app.config['PUBLIC_WEB_URL'] + 'reset-password?token=' + reset_link.token

        email_api.send_reset_password(email, user.first_name, link)

        return self.no_content()

    @handle_exceptions
    @password_setup_route.expect(password_setup_request)
    @password_setup_route.response(200, "Successfully set the users password.", password_setup_response)
    @password_setup_route.response(400, "Bad Request", message_response_dto)
    def post(self) -> Response:
        """Setup a password after user creation or password reset"""
        request_body = request.get_json()

        # expire old and validate
        self._purge_expired_tokens()
        password_token, password = self.validate_password_setup_request(request_body)

        # set password
        user = user_service.get_by_id(password_token.user_id)

        # only reset if the password hasn't been set (or has been reset)
        with session_scope() as session:
            user.set_password(password)
            session.delete(password_token)

        return self.ok({"email": user.email})

    @staticmethod
    def _purge_expired_tokens() -> None:
        """Removes password tokens that have expired."""
        with session_scope() as session:
            delete_expired = session.query(UserPasswordToken).filter(
                (UserPasswordToken.expire_after + UserPasswordToken.created_at) < int(time.time())
            ).delete()
            if delete_expired > 0:
                logger.info(f"Purged {delete_expired} password tokens which expired.")
