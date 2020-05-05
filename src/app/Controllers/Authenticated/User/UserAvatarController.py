import os

import boto3
from botocore.exceptions import ClientError
from flask import current_app, request
from flask_restx import Namespace

from app.Controllers.Base import RequestValidationController
from app.Decorators import requires_jwt, authorize
from app.Extensions.Errors import ValidationError, InternalServerError
from app.Models.Dao import User
from app.Models.Enums import Operations, Resources

api = Namespace(path="/user/avatar", name="User", description="Manage a user")

s3 = boto3.client("s3")


@api.route("/")
class UserAvatarController(RequestValidationController):
    @requires_jwt
    @authorize(Operations.UPDATE, Resources.USER)
    @api.response(200, "Success")
    def post(self, **kwargs):
        """Sets the avatar for a user"""
        req_user: User = kwargs["req_user"]

        if "file" not in request.files:
            raise ValidationError("Missing file part from request")

        file = request.files["file"]

        if file.filename == "":
            raise ValidationError("No file selected")

        if file.filename.rsplit('.', 1)[1].lower() not in ["jpg", "jpeg"]:
            raise ValidationError("Allowed file types are .png, .jpg, and .jpeg")

        try:
            s3.upload_fileobj(file, "assets.delegator.com.au", f"user/avatar/{req_user.uuid}.jpg")
        except ClientError as e:
            current_app.logger.error(f"error uploading profile avatar - {e}")
            raise InternalServerError("Unable to upload profile avatar")

        current_app.logger.info(f"Uploaded avatar {req_user.uuid}.jpg")

        return "", 204
