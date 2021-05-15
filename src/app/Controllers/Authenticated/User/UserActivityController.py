import structlog
from flask_restx import Namespace, fields

from app.Controllers.Base import RequestValidationController
from app.Decorators import requires_jwt, authorize
from app.Models.Enums import Operations, Resources

api = Namespace(path="/user/activity", name="User", description="Manage a user")
log = structlog.getLogger()


@api.route("/<int:user_id>")
class UserActivityController(RequestValidationController):

    activity_dto = api.model(
        "Activity",
        {"activity": fields.String(), "activity_timestamp": fields.String(), "event_friendly": fields.String()},
    )
    activity_response_dto = api.model("Activity Model", {"activity": fields.List(fields.Nested(activity_dto))})

    @requires_jwt
    @authorize(Operations.GET, Resources.USER_ACTIVITY)
    @api.marshal_with(activity_response_dto, code=200)
    def get(self, user_id: int, **kwargs):
        """Returns the activity for a user"""
        req_user = kwargs["req_user"]

        # TODO limit the history based on plan
        # subscription = Subscription(req_user.orgs.chargebee_subscription_id)

        user = self.validate_get_user_activity(user_id, **kwargs)
        req_user.log(Operations.GET, Resources.USER_ACTIVITY, resource_id=user.id)
        log.info(f"getting activity for user with id {user.id}")
        return {"activity": user.activity()}, 200
