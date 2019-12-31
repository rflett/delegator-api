from app.Controllers.Authenticated.User.UserActivityController import user_activity_route
from app.Controllers.Authenticated.User.UserController import user_route
from app.Controllers.Authenticated.User.UserPagesController import user_pages_route
from app.Controllers.Authenticated.User.UserSettingsController import user_settings_route
from app.Controllers.Authenticated.User.UsersController import users_route
from app.Controllers.Authenticated.User.UserWelcomeController import user_welcome_route


all_user_routes = [
    user_activity_route,
    user_route,
    user_pages_route,
    users_route,
    user_settings_route,
    user_welcome_route,
]
