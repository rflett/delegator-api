import structlog
from flask_restx import Namespace

from app.Controllers.Base import RequestValidationController
from app.Decorators import requires_jwt, authorize
from app.Models import Notification
from app.Models.Enums import TaskStatuses, Operations, Resources, Events
from app.Models.Enums.Notifications import TargetTypes

api = Namespace(path="/task/cancel", name="Task", description="Manage a task")
log = structlog.getLogger()


@api.route("/<int:task_id>")
class CancelTask(RequestValidationController):
    @requires_jwt
    @authorize(Operations.CANCEL, Resources.TASK)
    @api.response(204, "Success")
    def post(self, task_id: int, **kwargs):
        """Cancels a task"""
        req_user = kwargs["req_user"]

        # validate
        task_to_cancel = self.check_task_id(task_id, kwargs["req_user"].org_id)
        self.check_auth_scope(task_to_cancel.assigned_user, **kwargs)

        # transition
        task_to_cancel.transition(status=TaskStatuses.CANCELLED, req_user=req_user)
        req_user.log(Operations.CANCEL, Resources.TASK, resource_id=task_id)

        # send notifications if required
        if task_to_cancel.assignee is not None:
            cancelled_notification = Notification(
                title="Task cancelled",
                event_name=Events.task_transitioned_cancelled,
                target_id=task_to_cancel.id,
                target_type=TargetTypes.TASK,
                msg=f"{task_to_cancel.title} was cancelled by {req_user.name()}.",
                user_ids=[task_to_cancel.assignee],
                actions=[],
            )
            cancelled_notification.push()

        log.info(f"User {req_user.id} cancelled task {task_to_cancel.id}")
        return "", 204
