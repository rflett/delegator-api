from flask import request
from flask_restx import Namespace

from app.Controllers.Base import RequestValidationController
from app.Decorators import requires_jwt, authorize
from app.Extensions.Errors import ValidationError
from app.Models.Dao import User
from app.Models.Enums import Operations, Resources

api = Namespace(path="/user/avatar", name="User", description="Manage a user")


@api.route("/")
class UserAvatarController(RequestValidationController):
    @requires_jwt
    @authorize(Operations.UPDATE, Resources.USER)
    @api.response(204, "Success")
    def post(self, **kwargs):
        """Sets the avatar for the requesting user"""
        req_user: User = kwargs["req_user"]

        if "file" not in request.files:
            raise ValidationError("Missing file part from request")

        file = request.files["file"]

        if file.filename == "":
            raise ValidationError("No file selected")

        if file.filename.rsplit(".", 1)[1].lower() not in ["jpg", "jpeg"]:
            raise ValidationError("Allowed file types are .png, .jpg, and .jpeg")

        req_user.set_avatar(file)

        return "", 204

    @requires_jwt
    @authorize(Operations.UPDATE, Resources.USER)
    @api.response(204, "Success")
    def delete(self, **kwargs):
        """Resets the avatar for the requesting user"""
        req_user: User = kwargs["req_user"]
        req_user.reset_avatar()
        return "", 204
