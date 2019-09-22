from flask import Response
from flask_restplus import Namespace

from app import subscription_api, logger
from app.Controllers.Base import RequestValidationController
from app.Decorators import requires_jwt, handle_exceptions, authorize
from app.Exceptions import ProductTierLimitError
from app.Models.Enums import Operations, Resources
from app.Models.Response import message_response_dto, activity_response_dto

user_activity_route = Namespace(
    path="/user/activity",
    name="User Activity",
    description="Used to retrieve the activity for a user"
)


@user_activity_route.route("/<int:user_id>")
class UserActivityController(RequestValidationController):

    @requires_jwt
    @handle_exceptions
    @authorize(Operations.GET, Resources.USER_ACTIVITY)
    @user_activity_route.response(200, "User activity retrieved", activity_response_dto)
    @user_activity_route.response(400, "Couldn't retrieve User activity", message_response_dto)
    @user_activity_route.response(402, "Plan doesn't include this functionality", message_response_dto)
    def get(self, user_id: int, **kwargs) -> Response:
        """Returns the activity for a user """
        req_user = kwargs['req_user']

        if not subscription_api.get_limits(req_user.orgs.chargebee_subscription_id).get('view_user_activity', False):
            raise ProductTierLimitError(f"You cannot view user activity on your plan.")

        user = self.validate_get_user_activity(user_id, **kwargs)

        req_user.log(
            operation=Operations.GET,
            resource=Resources.USER_ACTIVITY,
            resource_id=user.id
        )
        logger.info(f"getting activity for user with id {user.id}")
        return self.ok({
            "activity": user.activity()
        })
