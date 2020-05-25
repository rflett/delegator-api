from flask import current_app
from flask_restx import Namespace, fields

from app.Controllers.Base import RequestValidationController
from app.Decorators import authorize, requires_jwt
from app.Extensions.Database import session_scope
from app.Models import Event
from app.Models.Enums import Operations, Resources, Events

api = Namespace(path="/user", name="User", description="Manage a user")


class NullableDateTime(fields.DateTime):
    __schema_type__ = ["string", "null"]
    __schema_example__ = "None|2019-09-17T19:08:00+10:00"


@api.route("/<int:user_id>")
class UserController(RequestValidationController):
    response_roles = ["ORG_ADMIN", "MANAGER", "STAFF", "USER", "LOCKED"]
    role_dto = api.model(
        "Get User Role",
        {
            "id": fields.String(enum=["ADMIN", "DELEGATOR", "USER", "LOCKED"]),
            "rank": fields.Integer(min=0, max=2),
            "name": fields.String(enum=["Admin", "Delegator", "User", "Locked"]),
            "description": fields.String(),
        },
    )
    user_response = api.model(
        "User Response",
        {
            "id": fields.Integer,
            "uuid": fields.String(),
            "org_id": fields.Integer,
            "email": fields.String,
            "first_name": fields.String,
            "last_name": fields.String,
            "role": fields.Nested(role_dto),
            "disabled": NullableDateTime,
            "job_title": fields.String,
            "created_at": fields.String,
            "created_by": fields.String,
            "updated_at": NullableDateTime,
            "updated_by": fields.String(),
            "invite_accepted": fields.Boolean,
        },
    )

    @requires_jwt
    @authorize(Operations.GET, Resources.USER)
    @api.marshal_with(user_response, code=200)
    def get(self, user_id: int, **kwargs):
        """Get a single user by email or ID """
        user = self.validate_get_user(user_id, **kwargs)
        kwargs["req_user"].log(Operations.GET, Resources.USER, resource_id=user.id)
        return user.fat_dict(), 200

    @requires_jwt
    @authorize(Operations.DELETE, Resources.USER)
    @api.response(204, "Success")
    def delete(self, user_id: int, **kwargs):
        """Deletes a user """
        req_user = kwargs["req_user"]

        user_to_delete = self.validate_delete_user(user_id, **kwargs)

        user_to_delete.delete(req_user)

        with session_scope():
            Event(
                org_id=req_user.org_id,
                event=Events.user_deleted_user,
                event_id=req_user.id,
                event_friendly=f"Deleted user {user_to_delete.name()}.",
            ).publish()

        req_user.log(Operations.DELETE, Resources.USER, resource_id=user_to_delete.id)

        current_app.logger.info(f"User {req_user.id} deleted user {user_to_delete.id}")
        return "", 204
