from flask import Response
from flask_restplus import Namespace

from app import session_scope, logger
from app.Controllers.Base import RequestValidationController
from app.Decorators import authorize, handle_exceptions, requires_jwt
from app.Models import Activity
from app.Models.Enums import Operations, Resources, Events
from app.Models.Response import message_response_dto, user_response

user_route = Namespace(path="/user", name="User", description="Manage a user")


@user_route.route("/<int:user_id>")
class UserController(RequestValidationController):
    @handle_exceptions
    @requires_jwt
    @authorize(Operations.GET, Resources.USER)
    @user_route.response(200, "Retrieved the user", user_response)
    @user_route.response(400, "Bad request", message_response_dto)
    @user_route.response(403, "Insufficient privileges", message_response_dto)
    @user_route.response(404, "User does not exist", message_response_dto)
    def get(self, user_id: int, **kwargs) -> Response:
        """Get a single user by email or ID """
        user = self.validate_get_user(user_id, **kwargs)
        kwargs["req_user"].log(operation=Operations.GET, resource=Resources.USER, resource_id=user.id)
        return self.ok(user.fat_dict())

    @handle_exceptions
    @requires_jwt
    @authorize(Operations.DELETE, Resources.USER)
    @user_route.response(204, "Successfully deleted the user")
    @user_route.response(400, "Bad request", message_response_dto)
    @user_route.response(403, "Insufficient privileges", message_response_dto)
    @user_route.response(404, "User does not exist", message_response_dto)
    def delete(self, user_id: int, **kwargs) -> Response:
        """Deletes a user """
        req_user = kwargs["req_user"]

        user_to_delete = self.validate_delete_user(user_id, **kwargs)

        user_to_delete.delete(req_user)

        with session_scope():
            Activity(
                org_id=req_user.org_id,
                event=Events.user_deleted_user,
                event_id=req_user.id,
                event_friendly=f"Deleted user {user_to_delete.name()}.",
            ).publish()

        req_user.log(operation=Operations.DELETE, resource=Resources.USER, resource_id=user_to_delete.id)

        logger.info(f"User {req_user.id} deleted user {user_to_delete.id}")
        return self.no_content()
