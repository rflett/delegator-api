import datetime

import structlog
from flask import request
from flask_restx import Namespace, fields
from sqlalchemy import desc

from app.Controllers.Base import RequestValidationController
from app.Decorators import requires_jwt, authorize
from app.Extensions.Database import session_scope
from app.Models import Notification, NotificationAction
from app.Models.Dao import DelayedTask, User, Task
from app.Models.Enums import TaskStatuses, Operations, Resources, Events
from app.Models.Enums.Notifications import ClickActions, TargetTypes
from app.Models.Enums.Notifications.NotificationIcons import NotificationIcons
from app.Utilities.All import get_task_by_id

api = Namespace(path="/task/delay", name="Task", description="Manage a task")
log = structlog.getLogger()


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
        request_body = request.get_json()

        task = self.validate_delay_task_request(**kwargs)
        reason = request_body["reason"]
        delay_for = request_body["delay_for"]

        with session_scope() as session:
            # transition a task to delayed
            task.transition(status=TaskStatuses.DELAYED, req_user=req_user)
            # check to see if the task has been delayed previously
            delay = session.query(DelayedTask).filter_by(task_id=task.id, expired=None).first()

            # if the task has been delayed before, expire it
            if delay is not None:
                delay.expired = datetime.datetime.utcnow()

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
            msg=f"{task.title} was delayed by {req_user.name()}.",
            target_type=TargetTypes.TASK,
            target_id=task.id,
            actions=[NotificationAction(ClickActions.VIEW_TASK, NotificationIcons.ASSIGN_TO_ME_ICON)],
        )
        if req_user.id == task.assignee:
            delayed_notification.user_ids = [task.created_by]
            delayed_notification.push()
        elif req_user.id == task.created_by:
            delayed_notification.user_ids = [task.assignee]
            delayed_notification.push()

        req_user.log(Operations.DELAY, Resources.TASK, resource_id=task.id)
        log.info(f"User {req_user.id} delayed task {task.id} for {delay_for}s.")
        return "", 204


@api.route("/<int:task_id>")
class GetDelayTask(RequestValidationController):
    class NullableDateTime(fields.DateTime):
        __schema_type__ = ["string", "null"]
        __schema_example__ = "None|2019-09-17T19:08:00+10:00"

    delayed_task_dto = api.model(
        "Delayed Task Dto",
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
    response_dto = api.model("Delayed Tasks Response", {"tasks": fields.List(fields.Nested(delayed_task_dto))})

    @requires_jwt
    @authorize(Operations.GET, Resources.TASK)
    @api.marshal_with(response_dto, code=200)
    def get(self, task_id: int, **kwargs):
        """Returns the delayed info for a task """
        req_user = kwargs["req_user"]

        ret = []

        with session_scope() as session:
            qry = (
                session.query(DelayedTask, User.first_name, User.last_name)
                .join(Task, DelayedTask.task_id == task_id)
                .join(User, DelayedTask.delayed_by == User.id)
                .filter(Task.org_id == req_user.org_id)
                .order_by(desc(DelayedTask.delayed_at))
                .all()
            )

        for result in qry:
            task, db_fn, db_ln = result
            delayed_task_dict = task.as_dict()
            delayed_task_dict["delayed_by"] = db_fn + " " + db_ln
            ret.append(delayed_task_dict)

        task = get_task_by_id(task_id, req_user.org_id)
        req_user.log(Operations.GET, Resources.TASK, resource_id=task.id)

        return {"tasks": ret}, 200
