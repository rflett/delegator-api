from decimal import Decimal

from flask import Response, request
from flask_restx import Namespace

from app import logger
from app.Controllers.Base import RequestValidationController
from app.Decorators import requires_jwt, handle_exceptions, authorize
from app.Models import UserSetting
from app.Models.Enums import Operations, Resources
from app.Models.Response import message_response_dto
from app.Models.Response.Account import user_settings_response
from app.Services.SettingsService import SettingsService

user_settings_route = Namespace(path="/user/settings", name="User", description="Manage a user")

settings_service = SettingsService()


@user_settings_route.route("/")
class UserSettingsController(RequestValidationController):
    @handle_exceptions
    @requires_jwt
    @authorize(Operations.GET, Resources.USER_SETTINGS)
    @user_settings_route.response(200, "User settings retrieved", user_settings_response)
    @user_settings_route.response(400, "Failed to retrieve settings", message_response_dto)
    @user_settings_route.response(403, "Insufficient privileges", message_response_dto)
    def get(self, **kwargs) -> Response:
        """Returns the user's settings"""
        req_user = kwargs["req_user"]
        req_user.log(operation=Operations.GET, resource=Resources.USER_SETTINGS, resource_id=req_user.id)
        logger.info(f"got user settings for {req_user.id}")
        return self.ok(settings_service.get_user_settings(req_user.id).as_dict())

    @handle_exceptions
    @requires_jwt
    @authorize(Operations.UPDATE, Resources.USER_SETTINGS)
    @user_settings_route.expect(user_settings_response)
    @user_settings_route.response(200, "User settings updated", user_settings_response)
    @user_settings_route.response(400, "Failed to update settings", message_response_dto)
    @user_settings_route.response(403, "Insufficient privileges", message_response_dto)
    @user_settings_route.response(404, "User does not exist", message_response_dto)
    def put(self, **kwargs) -> Response:
        """Updates the user's settings"""
        req_user = kwargs["req_user"]

        new_settings = UserSetting(user_id=Decimal(req_user.id))
        for k, v in request.get_json().items():
            new_settings.__setattr__(k, v)

        settings_service.set_user_settings(new_settings)
        req_user.log(operation=Operations.UPDATE, resource=Resources.USER_SETTINGS, resource_id=req_user.id)
        logger.info(f"updated user {req_user.id} settings")
        return self.ok(new_settings.as_dict())
