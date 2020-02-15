import datetime

from flask import current_app
from flask_restx import Namespace, fields

from app.Controllers.Base import RequestValidationController
from app.Decorators import requires_jwt, authorize
from app.Extensions.Database import session_scope
from app.Models import DelayedTask, Notification
from app.Models.Enums import TaskStatuses, Operations, Resources, Events, ClickActions
from app.Services import TaskService

api = Namespace(path="/task/delay", name="Task", description="Manage a task")

task_service = TaskService()


@api.route("/")
class DelayTask(RequestValidationController):

    request_dto = api.model(
        "Delay Task Request",
        {
            "task_id": fields.Integer(required=True),
            "delay_for": fields.Integer(required=True),
            "reason": fields.String(required=True),
        },
    )

    @requires_jwt
    @authorize(Operations.DELAY, Resources.TASK)
    @api.expect(request_dto, validate=True)
    @api.response(204, "Success")
    def put(self, **kwargs):
        """Delays a task """
        req_user = kwargs["req_user"]

        task, delay_for, reason = self.validate_delay_task_request(**kwargs)

        with session_scope() as session:
            # transition a task to delayed
            task_service.transition(task=task, status=TaskStatuses.DELAYED, req_user=req_user)
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
                    reason=reason,
                )
                session.add(delayed_task)

        # send notifications
        delayed_notification = Notification(
            title="Task delayed",
            event_name=Events.task_transitioned_delayed,
            msg=f"{task.label()} was delayed by {req_user.name()}.",
            click_action=ClickActions.VIEW_TASK,
            task_action_id=task.id,
        )
        if req_user.id == task.assignee:
            delayed_notification.user_ids = task.created_by
            delayed_notification.push()
        elif req_user.id == task.created_by:
            delayed_notification.user_ids = task.assignee
            delayed_notification.push()

        req_user.log(operation=Operations.DELAY, resource=Resources.TASK, resource_id=task.id)
        current_app.logger.info(f"User {req_user.id} delayed task {task.id} for {delay_for}s.")
        return "", 204


@api.route("/<int:task_id>")
class GetDelayTask(RequestValidationController):
    class NullableDateTime(fields.DateTime):
        __schema_type__ = ["datetime", "null"]
        __schema_example__ = "None|2019-09-17T19:08:00+10:00"

    response_dto = api.model(
        "Delayed Tasks Response",
        {
            "task_id": fields.Integer(),
            "delay_for": fields.Integer(),
            "delayed_at": fields.DateTime(),
            "delayed_by": fields.String(),
            "reason": fields.String(),
            "snoozed": NullableDateTime,
            "expired": NullableDateTime,
        },
    )

    @requires_jwt
    @authorize(Operations.GET, Resources.TASK)
    @api.marshal_with(response_dto, code=200)
    def get(self, task_id: int, **kwargs):
        """Returns the delayed info for a task """
        req_user = kwargs["req_user"]
        task = task_service.get(task_id, req_user.org_id)
        req_user.log(operation=Operations.GET, resource=Resources.TASK, resource_id=task.id)
        return task.delayed_info(), 200
