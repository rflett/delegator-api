from flask_restplus import Namespace

from app import logger
from app.Decorators import authorize, requires_jwt, handle_exceptions
from app.Controllers.Base import RequestValidationController
from app.Models import Subscription
from app.Models.Enums import Operations, Resources
from app.Models.Response import message_response_dto, activity_response_dto
from app.Services import TaskService

task_activity_route = Namespace(
    path="/task/activity",
    name="Task",
    description="Manage a task"
)

task_service = TaskService()


@task_activity_route.route("/<int:task_id>")
class TaskActivity(RequestValidationController):

    @handle_exceptions
    @requires_jwt
    @authorize(Operations.GET, Resources.TASK_ACTIVITY)
    @task_activity_route.response(200, "Success", activity_response_dto)
    @task_activity_route.response(400, "Bad request", message_response_dto)
    @task_activity_route.response(403, "Insufficient privileges", message_response_dto)
    @task_activity_route.response(404, "Task not found", message_response_dto)
    def get(self, task_id: int, **kwargs):
        """Returns the activity for a task"""
        req_user = kwargs['req_user']

        # check the subscription limitations
        subscription = Subscription(req_user.orgs.chargebee_subscription_id)
        activity_log_history_limit = subscription.task_activity_log_history()

        # get the task
        task = task_service.get(task_id, req_user.org_id)
        req_user.log(
            operation=Operations.GET,
            resource=Resources.TASK_ACTIVITY,
            resource_id=task.id
        )
        logger.info(f"Getting activity for task with id {task.id}")
        return self.ok({
            "activity": task.activity(activity_log_history_limit)
        })