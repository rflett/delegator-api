import time

from flask import Response, request
from flask_restplus import Namespace

from app import session_scope, logger
from app.Decorators import handle_exceptions
from app.Controllers.Base import RequestValidationController
from app.Models import UserInviteLink
from app.Models.Response import new_password_setup_response, message_response_dto
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
    @password_setup_route.response(204, "No Content")
    @password_setup_route.response(400, "Bad Request", message_response_dto)
    def get(self):
        """Validates the token is valid and hasn't expired"""
        self._purge_expired_tokens()
        self.validate_password_setup_request()
        return self.no_content()

    @handle_exceptions
    @password_setup_route.response(200, "Success", new_password_setup_response)
    @password_setup_route.response(400, "Bad Request", message_response_dto)
    def post(self) -> Response:
        """Setup a password after user creation or password reset"""
        request_body = request.get_json()

        # expire old and validate
        self._purge_expired_tokens()
        user_invite_link = self.validate_password_setup_request()

        # validate password
        password = self.validate_password(request_body.get('password'))

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
