import datetime
import pytz
from dateutil import tz

from flask import current_app
from flask_restx import Namespace, fields
from sqlalchemy import and_, or_
from sqlalchemy.orm import aliased

from app.Controllers.Base import RequestValidationController
from app.Decorators import requires_jwt, authorize
from app.Extensions.Database import session_scope
from app.Models.Dao import User, Task, TaskLabel
from app.Models.Enums import Operations, Resources
from app.Services import TaskService

api = Namespace(path="/tasks", name="Tasks", description="Manage tasks")

task_service = TaskService()


class NullableDateTime(fields.DateTime):
    __schema_type__ = ["string", "null"]
    __schema_example__ = "None|2019-09-17T19:08:00+10:00"


@api.route("/")
class Tasks(RequestValidationController):
    task_label_dto = api.model(
        "Get Tasks Label Dto", {"id": fields.Integer(), "label": fields.String(), "colour": fields.String()}
    )
    user_dto = api.model(
        "Task User Dto",
        {"id": fields.Integer(), "uuid": fields.String(), "first_name": fields.String(), "last_name": fields.String()},
    )
    task_dto = api.model(
        "Get Tasks Dto",
        {
            "id": fields.Integer(),
            "title": fields.String(),
            "description": fields.String(),
            "status": fields.String(),
            "scheduled_for": NullableDateTime,
            "assignee": fields.Nested(user_dto, allow_null=True),
            "priority": fields.Integer(),
            "display_order": fields.Integer(),
            "scheduled_notification_period": fields.Integer(),
            "scheduled_notification_sent": NullableDateTime(),
            "time_estimate": fields.Integer(),
            "labels": fields.List(fields.Nested(task_label_dto)),
        },
    )
    response_dto = api.model("Tasks Response", {"tasks": fields.List(fields.Nested(task_dto))})

    @requires_jwt
    @authorize(Operations.GET, Resources.TASKS)
    @api.marshal_with(response_dto, code=200)
    def get(self, **kwargs):
        """Get all tasks"""
        req_user = kwargs["req_user"]

        # start_period, end_period = self.validate_time_period(req.get_json())
        end_period = now = datetime.datetime.utcnow()
        start_period = datetime.datetime(now.year, now.month, 1, tzinfo=tz.tzutc())  # start_of_this_month

        with session_scope() as session:
            label1, label2, label3 = aliased(TaskLabel), aliased(TaskLabel), aliased(TaskLabel)
            tasks_qry = (
                session.query(
                    Task.id,
                    Task.title,
                    Task.description,
                    Task.priority,
                    Task.scheduled_for,
                    Task.status,
                    Task.display_order,
                    Task.time_estimate,
                    Task.scheduled_notification_period,
                    Task.scheduled_notification_sent,
                    User.id,
                    User.uuid,
                    User.first_name,
                    User.last_name,
                    label1,
                    label2,
                    label3,
                )
                .outerjoin(User, User.id == Task.assignee)
                .outerjoin(label1, label1.id == Task.label_1)
                .outerjoin(label2, label2.id == Task.label_2)
                .outerjoin(label3, label3.id == Task.label_3)
                .filter(
                    and_(
                        Task.org_id == req_user.org_id,
                        or_(
                            and_(Task.finished_at >= start_period, Task.finished_at <= end_period),
                            Task.finished_at == None,  # noqa
                        ),
                    )
                )
                .order_by(Task.display_order)
                .all()
            )

        tasks = []

        for task in tasks_qry:
            (
                id_,
                title,
                description,
                priority,
                scheduled_for,
                status,
                display_order,
                time_estimate,
                scheduled_noti_period,
                scheduled_noti_sent,
                assignee_id,
                assignee_uuid,
                assignee_fn,
                assignee_ln,
                label_1,
                label_2,
                label_3,
            ) = task

            # convert labels to a list
            labels = [label.as_dict() for label in [label_1, label_2, label_3] if label is not None]

            # convert dates
            if scheduled_for is not None:
                scheduled_for = pytz.utc.localize(scheduled_for)
                scheduled_for = scheduled_for.strftime(current_app.config["RESPONSE_DATE_FORMAT"])

            if scheduled_noti_sent is not None:
                scheduled_noti_sent = pytz.utc.localize(scheduled_noti_sent)
                scheduled_noti_sent = scheduled_noti_sent.strftime(current_app.config["RESPONSE_DATE_FORMAT"])

            if assignee_id is None:
                assignee = None
            else:
                assignee = {
                    "id": assignee_id,
                    "uuid": assignee_uuid,
                    "first_name": assignee_fn,
                    "last_name": assignee_ln,
                }

            tasks.append(
                {
                    "id": id_,
                    "title": title,
                    "description": description,
                    "priority": priority,
                    "status": status,
                    "display_order": display_order,
                    "assignee": assignee,
                    "labels": labels,
                    "scheduled_for": scheduled_for,
                    "scheduled_notification_period": scheduled_noti_period,
                    "scheduled_notification_sent": scheduled_noti_sent,
                    "time_estimate": time_estimate,
                }
            )
        return {"tasks": tasks}, 200
