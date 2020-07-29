from decimal import Decimal

import structlog
from flask import request
from flask_restx import Namespace, fields

from app.Controllers.Base import RequestValidationController
from app.Decorators import requires_jwt, authorize
from app.Models import UserSetting
from app.Models.Enums import Operations, Resources

api = Namespace(path="/user/settings", name="User", description="Manage a user")
log = structlog.getLogger()


@api.route("/")
class UserSettingsController(RequestValidationController):

    user_settings_dto = api.model(
        "User Settings Response", {"user_id": fields.Integer(required=True), "tz_offset": fields.String(required=True)}
    )

    @requires_jwt
    @authorize(Operations.GET, Resources.USER_SETTINGS)
    @api.marshal_with(user_settings_dto, code=200)
    def get(self, **kwargs):
        """Returns the user's settings"""
        req_user = kwargs["req_user"]
        req_user.log(Operations.GET, Resources.USER_SETTINGS, resource_id=req_user.id)
        log.info(f"got user settings for {req_user.id}")
        user_setting = UserSetting(req_user.id)
        user_setting.get()
        return user_setting.as_dict(), 200

    @requires_jwt
    @authorize(Operations.UPDATE, Resources.USER_SETTINGS)
    @api.expect(user_settings_dto, validate=True)
    @api.response(204, "Success")
    def put(self, **kwargs):
        """Updates the user's settings"""
        req_user = kwargs["req_user"]
        request_body = request.get_json()

        user_setting = UserSetting(user_id=Decimal(req_user.id))
        user_setting.tz_offset = request_body["tz_offset"]
        user_setting.update()

        req_user.log(Operations.UPDATE, Resources.USER_SETTINGS, resource_id=req_user.id)
        log.info(f"updated user {req_user.id} settings")
        return "", 204
