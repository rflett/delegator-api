import structlog
from flask import request, current_app
from flask_restx import Namespace, fields

from app.Controllers.Base import RequestValidationController
from app.Decorators import authorize, requires_jwt
from app.Extensions.Errors import ValidationError
from app.Models import Email
from app.Models.Enums import Operations, Resources

api = Namespace(path="/user", name="User", description="Manage a user")
log = structlog.getLogger()


@api.route("/resend-welcome")
class UserController(RequestValidationController):
    request_dto = api.model("Resend Welcome Request", {"user_id": fields.Integer(required=True)})

    @requires_jwt
    @authorize(Operations.UPDATE, Resources.USER)
    @api.expect(request_dto, validate=True)
    @api.response(204, "Success")
    def post(self, **kwargs):
        """Resend the welcome email for a user"""
        request_body = request.get_json()
        req_user = kwargs["req_user"]

        user = self.check_user_id(request_body.get("user_id"), should_exist=True)

        if user.invite_accepted():
            raise ValidationError("User has already accepted their invitation.")

        token = user.generate_new_invite()

        # resend
        email = Email(user.email)
        email.send_welcome_new_user(
            first_name=user.first_name,
            link=current_app.config["PUBLIC_WEB_URL"] + "/account-setup?token=" + token.token,
            inviter=req_user,
        )

        log.info(f"User {req_user.id} resent verification email to user {user.id}.")
        req_user.log(Operations.UPDATE, Resources.USER, resource_id=user.id)

        return "", 204
