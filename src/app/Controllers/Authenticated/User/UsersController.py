from flask_restplus import Namespace

from app.Controllers.Base import RequestValidationController

users_route = Namespace(
    path="/users",
    name="Users",
    description="Used to manage users"
)


@users_route.route("/")
class UserController(RequestValidationController):
