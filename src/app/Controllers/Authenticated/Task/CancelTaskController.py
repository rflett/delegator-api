from flask import Response
from flask_restplus import Namespace

from app import logger
from app.Controllers.Base import RequestValidationController
from app.Decorators import requires_jwt, handle_exceptions, authorize
from app.Models import Notification
from app.Models.Enums import TaskStatuses, Operations, Resources, ClickActions, Events
from app.Models.Response import task_response, message_response_dto
from app.Services import TaskService

cancel_task_route = Namespace(
    path="/task/cancel",
    name="Tasks",
    description="Manage tasks"
)

task_service = TaskService()


@cancel_task_route.route("/<int:task_id>")
class CancelTask(RequestValidationController):

    @handle_exceptions
    @requires_jwt
    @authorize(Operations.CANCEL, Resources.TASK)
    @cancel_task_route.response(200, "Success", task_response)
    @cancel_task_route.response(400, "Failed to cancel the task", message_response_dto)
    def post(self, task_id: int, **kwargs) -> Response:
        """Cancels a task"""
        req_user = kwargs['req_user']

        task_to_cancel = self.validate_cancel_task(task_id, **kwargs)

        task_service.transition(
            task=task_to_cancel,
            status=TaskStatuses.CANCELLED,
            req_user=req_user
        )
        req_user.log(
            operation=Operations.CANCEL,
            resource=Resources.TASK,
            resource_id=task_id
        )
        if task_to_cancel.assignee is not None:
            cancelled_notification = Notification(
                title="Task cancelled",
                event_name=Events.task_transitioned_cancelled,
                msg=f"{task_to_cancel.label()} was cancelled by {req_user.name()}.",
                user_ids=task_to_cancel.assignee,
                click_action=ClickActions.CLOSE
            )
            cancelled_notification.push()
        logger.info(f"User {req_user.id} cancelled task {task_to_cancel.id}")
        return self.ok(task_to_cancel.fat_dict())
