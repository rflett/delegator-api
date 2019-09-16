import datetime

from flask import request, Response
from flask_restplus import Namespace

from app import logger, session_scope
from app.Controllers.Base import RequestValidationController
from app.Decorators import requires_jwt, handle_exceptions, authorize
from app.Models import DelayedTask, Notification
from app.Models.Enums import TaskStatuses, Operations, Resources
from app.Models.Request import delay_task_dto, get_delayed_task_dto
from app.Models.Response import task_response_dto, message_response_dto, delayed_task_response_dto
from app.Services import TaskService

delay_task_route = Namespace(
    path="/task/delay",
    name="Tasks",
    description="Manage tasks"
)

task_service = TaskService()


@delay_task_route.route("/")
class DelayTask(RequestValidationController):

    @handle_exceptions
    @requires_jwt
    @authorize(Operations.DELAY, Resources.TASK)
    @delay_task_route.expect(delay_task_dto)
    @delay_task_route.response(200, "Success", task_response_dto)
    @delay_task_route.response(400, "Failed to delay the task", message_response_dto)
    def post(self, **kwargs) -> Response:
        """Delays a task """
        req_user = kwargs['req_user']

        task, delay_for, reason = self.validate_delay_task_request(request.get_json(), **kwargs)

        with session_scope() as session:
            # transition a task to delayed
            task_service.transition(
                task=task,
                status=TaskStatuses.DELAYED,
                req_user=req_user
            )
            # check to see if the task has been delayed previously
            delay = session.query(DelayedTask).filter_by(task_id=task.id).first()

            # if the task has been delayed before, update it, otherwise create it
            if delay is not None:
                delay.delay_for = delay_for
                delay.delayed_at = datetime.datetime.utcnow()
                delay.snoozed = None
                if reason is not None:
                    delay.reason = reason
            else:
                delayed_task = DelayedTask(
                    task_id=task.id,
                    delay_for=delay_for,
                    delayed_at=datetime.datetime.utcnow(),
                    delayed_by=req_user.id,
                    reason=reason
                )
                session.add(delayed_task)

        if req_user.id == task.assignee:
            Notification(
                msg=f"{task.label()} has been delayed.",
                user_ids=task.created_by
            ).push()
        elif req_user.id == task.created_by:
            Notification(
                msg=f"{task.label()} has been delayed.",
                user_ids=task.assignee
            ).push()

        req_user.log(
            operation=Operations.DELAY,
            resource=Resources.TASK,
            resource_id=task.id
        )
        logger.info(f"User {req_user.id} delayed task {task.id} for {delay_for}s.")
        return self.ok(task.fat_dict())

    @handle_exceptions
    @requires_jwt
    @authorize(Operations.GET, Resources.TASK)
    @delay_task_route.expect(get_delayed_task_dto)
    @delay_task_route.response(200, "Success", delayed_task_response_dto)
    @delay_task_route.response(400, "Failed to delay the task", message_response_dto)
    def get(self, **kwargs) -> Response:
        """Returns the delayed info for a task """
        req_user = kwargs['req_user']
        request_body = request.get_json()
        task_id = request_body.get('task_id')

        task = task_service.get(task_id, req_user.org_id)

        req_user.log(
            operation=Operations.GET,
            resource=Resources.TASK,
            resource_id=task.id
        )

        return self.ok(task.delayed_info())
