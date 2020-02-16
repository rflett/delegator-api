import datetime

from flask_restx import Namespace

from app.Controllers.Base import RequestValidationController
from app.Decorators import authorize, requires_jwt
from app.Extensions.Database import session_scope
from app.Extensions.Errors import ValidationError
from app.Models import Activity, Task, Subscription
from app.Models.Enums import Operations, Resources, Events

api = Namespace(path="/user/disable", name="User", description="Manage a user")


@api.route("/<int:user_id>")
class DisableUserController(RequestValidationController):
    @requires_jwt
    @authorize(Operations.UPDATE, Resources.USER)
    @api.response(204, "Success")
    def post(self, user_id: int, **kwargs):
        """Disable a user"""
        req_user = kwargs["req_user"]

        user_to_disable = self.validate_disable_user(user_id, **kwargs)

        if user_to_disable.disabled is not None:
            raise ValidationError("User is already disabled.")

        with session_scope() as session:
            user_to_disable.disabled = datetime.datetime.utcnow()
            users_tasks = session.query(Task).filter_by(assignee=user_to_disable.id).all()

        # drop tasks
        for task in users_tasks:
            task.drop(req_user)

        Activity(
            org_id=req_user.org_id,
            event=Events.user_disabled_user,
            event_id=req_user.id,
            event_friendly=f"Disabled user {user_to_disable.name()}.",
        ).publish()
        Activity(
            org_id=req_user.org_id,
            event=Events.user_disabled_user,
            event_id=user_to_disable.id,
            event_friendly=f"Disabled by {req_user.name()}.",
        ).publish()

        # decrement plan quantity
        subscription = Subscription(req_user.orgs.chargebee_subscription_id)
        subscription.decrement_subscription(req_user)

        req_user.log(operation=Operations.DISABLE, resource=Resources.USER, resource_id=user_to_disable.id)
        return "", 204

    @requires_jwt
    @authorize(Operations.UPDATE, Resources.USER)
    @api.response(204, "Success")
    def delete(self, user_id: int, **kwargs):
        """Enable a user """
        req_user = kwargs["req_user"]

        user_to_enable = self.check_user_id(user_id, should_exist=True)
        self.check_auth_scope(user_to_enable, **kwargs)

        if user_to_enable.disabled is None:
            raise ValidationError("User is not disabled.")

        with session_scope():
            user_to_enable.disabled = None

        Activity(
            org_id=req_user.org_id,
            event=Events.user_enabled_user,
            event_id=req_user.id,
            event_friendly=f"Enabled user {user_to_enable.name()}.",
        ).publish()
        Activity(
            org_id=req_user.org_id,
            event=Events.user_enabled_user,
            event_id=user_to_enable.id,
            event_friendly=f"Enabled by {req_user.name()}.",
        ).publish()

        # increment plan quantity
        subscription = Subscription(req_user.orgs.chargebee_subscription_id)
        subscription.increment_subscription(req_user)

        req_user.log(operation=Operations.ENABLE, resource=Resources.USER, resource_id=user_to_enable.id)
        return "", 204
