from flask_restplus import Namespace

from app.Controllers.Base import RequestValidationController

user_settings_route = Namespace(
    path="/user/settings",
    name="User Settings",
    description="Used to manage user settings"
)


@user_settings_route.route("/")
class UserSettingsController(RequestValidationController):
    def get(self):