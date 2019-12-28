import time

from flask import Response, request
from flask_restplus import Namespace

from app import session_scope, logger
from app.Controllers.Base import RequestValidationController
from app.Decorators import handle_exceptions
from app.Exceptions import ValidationError, ResourceNotFoundError
from app.Models import UserInviteLink
from app.Models.Request import password_setup_request
from app.Models.Response import password_setup_response, message_response_dto
from app.Services import UserService, EmailService

user_service = UserService()
email_service = EmailService()

password_setup_route = Namespace(
    path="/password",
    name="Password Management",
    description="Manage passwords"
)


@password_setup_route.route("/")
class PasswordSetup(RequestValidationController):

    @handle_exceptions
    @password_setup_route.param('invtkn', 'The token that the user received to manage their password.')
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
            session.query(UserInviteLink).filter_by(user_id=user.id).delete()
            # create new link
            reset_link = UserInviteLink(user.id)
            session.add(reset_link)
            # send email
            email_service.send_reset_password_email(user.email, reset_link.token)
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
        user_invite_link, password = self.validate_password_setup_request(request_body)

        # set password
        user = user_service.get_by_id(user_invite_link.user_id)

        # only reset if the password hasn't been set (or has been reset)
        with session_scope() as session:
            user.set_password(password)
            session.delete(user_invite_link)

        return self.ok({"email": user.email})

    @staticmethod
    def _purge_expired_tokens() -> None:
        """Removes invite tokens that have expired."""
        with session_scope() as session:
            delete_expired = session.query(UserInviteLink).filter(
                (UserInviteLink.expire_after + UserInviteLink.created_at) < int(time.time())
            ).delete()
            if delete_expired > 0:
                logger.info(f"Purged {delete_expired} invite links which expired.")
