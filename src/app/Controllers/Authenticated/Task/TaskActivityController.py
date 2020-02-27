from flask import current_app
from flask_restx import Namespace, fields

from app.Decorators import authorize, requires_jwt
from app.Controllers.Base import RequestValidationController
from app.Models import Subscription
from app.Models.Enums import Operations, Resources
from app.Services import TaskService

api = Namespace(path="/task/activity", name="Task", description="Manage a task")

task_service = TaskService()


@api.route("/<int:task_id>")
class TaskActivity(RequestValidationController):

    activity_dto = api.model(
        "Activity",
        {"activity": fields.String(), "activity_timestamp": fields.String(), "event_friendly": fields.String()},
    )

    response_dto = api.model("Activity Model", {"activity": fields.List(fields.Nested(activity_dto))})

    @requires_jwt
    @authorize(Operations.GET, Resources.TASK_ACTIVITY)
    @api.marshal_with(response_dto, code=200)
    def get(self, task_id: int, **kwargs):
        """Returns the activity for a task"""
        req_user = kwargs["req_user"]
        # check the subscription limitations
        subscription = Subscription(req_user.orgs.chargebee_subscription_id)
        activity_log_history_limit = subscription.task_activity_log_history()
        # get the task
        task = task_service.get(task_id, req_user.org_id)
        req_user.log(Operations.GET, Resources.TASK_ACTIVITY, resource_id=task.id)
        current_app.logger.info(f"Getting activity for task with id {task.id}")
        return {"activity": task.activity(activity_log_history_limit)}, 200
