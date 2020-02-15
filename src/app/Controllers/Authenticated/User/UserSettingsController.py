from decimal import Decimal

from flask import request, current_app
from flask_restx import Namespace, fields

from app.Controllers.Base import RequestValidationController
from app.Decorators import requires_jwt, authorize
from app.Models import UserSetting
from app.Models.Enums import Operations, Resources
from app.Services.SettingsService import SettingsService

api = Namespace(path="/user/settings", name="User", description="Manage a user")

settings_service = SettingsService()


@api.route("/")
class UserSettingsController(RequestValidationController):

    user_settings_dto = api.model("User Settings Response", {"user_id": fields.Integer(required=True), "tz_offset": fields.String(required=True)})

    @requires_jwt
    @authorize(Operations.GET, Resources.USER_SETTINGS)
    @api.marshal_with(user_settings_dto, code=200)
    def get(self, **kwargs):
        """Returns the user's settings"""
        req_user = kwargs["req_user"]
        req_user.log(operation=Operations.GET, resource=Resources.USER_SETTINGS, resource_id=req_user.id)
        current_app.logger.info(f"got user settings for {req_user.id}")
        return settings_service.get_user_settings(req_user.id).as_dict(), 200

    @requires_jwt
    @authorize(Operations.UPDATE, Resources.USER_SETTINGS)
    @api.expect(user_settings_dto, validate=True)
    @api.response(204, "Success")
    def put(self, **kwargs):
        """Updates the user's settings"""
        req_user = kwargs["req_user"]
        request_body = request.get_json()

        new_settings = UserSetting(user_id=Decimal(req_user.id))
        new_settings.tz_offset = request_body["tz_offset"]
        settings_service.set_user_settings(new_settings)

        req_user.log(operation=Operations.UPDATE, resource=Resources.USER_SETTINGS, resource_id=req_user.id)
        current_app.logger.info(f"updated user {req_user.id} settings")
        return "", 204
