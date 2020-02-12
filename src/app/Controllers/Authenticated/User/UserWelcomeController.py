from flask import Response, request
from flask_restx import Namespace

from app import logger, app
from app.Controllers.Base import RequestValidationController
from app.Decorators import authorize, handle_exceptions, requires_jwt
from app.Models import Email
from app.Models.Enums import Operations, Resources
from app.Models.Request import resend_welcome_request
from app.Models.Response import message_response_dto

user_welcome_route = Namespace(path="/user", name="User", description="Manage a user")


@user_welcome_route.route("/resend-welcome")
class UserController(RequestValidationController):
    @handle_exceptions
    @requires_jwt
    @authorize(Operations.UPDATE, Resources.USER)
    @user_welcome_route.expect(resend_welcome_request)
    @user_welcome_route.response(204, "Sent")
    @user_welcome_route.response(400, "Bad request", message_response_dto)
    @user_welcome_route.response(403, "Insufficient privileges", message_response_dto)
    @user_welcome_route.response(404, "Resource does not exist", message_response_dto)
    def post(self, **kwargs) -> Response:
        """Resend the welcome email for a user"""
        request_body = request.get_json()
        req_user = kwargs["req_user"]

        user, token = self.validate_resend_welcome_request(request_body)

        # resend
        email = Email(user)
        email.send_welcome_new_user(
            link=app.config["PUBLIC_WEB_URL"] + "/account-setup?token=" + token,
            inviter=req_user
        )

        logger.info(f"User {req_user.id} resent verification email to user {user.id}.")

        req_user.log(operation=Operations.UPDATE, resource=Resources.USER, resource_id=user.id)

        return self.no_content()
