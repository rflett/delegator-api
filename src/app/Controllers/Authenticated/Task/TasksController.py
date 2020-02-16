import datetime
from dateutil import tz

from flask import current_app
from flask_restx import Namespace, fields
from sqlalchemy import and_, or_
from sqlalchemy.orm import aliased

from app.Controllers.Base import RequestValidationController
from app.Decorators import requires_jwt, authorize
from app.Extensions.Database import session_scope
from app.Models.Dao import User, Task, TaskLabel, TaskType
from app.Models.Enums import Operations, Resources
from app.Services import TaskService

api = Namespace(path="/tasks", name="Tasks", description="Manage tasks")

task_service = TaskService()


class NullableDateTime(fields.DateTime):
    __schema_type__ = ["datetime", "null"]
    __schema_example__ = "None|2019-09-17T19:08:00+10:00"


@api.route("/")
class Tasks(RequestValidationController):

    task_label_dto = api.model(
        "Get Tasks Label Dto", {"id": fields.Integer(), "label": fields.String(), "colour": fields.String()}
    )
    task_dto = api.model(
        "Get Tasks Dto",
        {
            "id": fields.Integer(),
            "type": fields.String(),
            "description": fields.String(),
            "status": fields.String(),
            "scheduled_for": NullableDateTime,
            "assignee": fields.String(),
            "assignee_id": fields.Integer(),
            "priority": fields.Integer(),
            "labels": fields.List(fields.Nested(task_label_dto)),
        },
    )
    response_dto = api.model("Tasks Response", {"tasks": fields.List(fields.Nested(task_dto))})

    @requires_jwt
    @authorize(Operations.GET, Resources.TASKS)
    @api.marshal_with(response_dto, code=200)
    def get(self, **kwargs):
        """Get all tasks in an organisation with minimal info"""
        req_user = kwargs["req_user"]

        # start_period, end_period = self.validate_time_period(req.get_json())
        end_period = now = datetime.datetime.utcnow()
        start_period = datetime.datetime(now.year, now.month, 1, tzinfo=tz.tzutc())  # start_of_this_month

        with session_scope() as session:
            label1, label2, label3 = aliased(TaskLabel), aliased(TaskLabel), aliased(TaskLabel)
            tasks_qry = (
                session.query(
                    Task.id,
                    Task.description,
                    Task.priority,
                    Task.scheduled_for,
                    Task.status,
                    TaskType.label,
                    User.id,
                    User.first_name,
                    User.last_name,
                    label1,
                    label2,
                    label3,
                )
                .join(TaskType, TaskType.id == Task.type)
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
                .all()
            )

        tasks = []

        for task in tasks_qry:
            (
                id_,
                description,
                priority,
                scheduled_for,
                status,
                type_,
                assignee_id,
                assignee_fn,
                assignee_ln,
                label_1,
                label_2,
                label_3,
            ) = task

            # assignee is either null, or return their first and last name concat
            if assignee_fn is None and assignee_ln is None:
                assignee = None
            else:
                assignee = assignee_fn + " " + assignee_ln

            # convert labels to a list
            labels = [l.as_dict() for l in [label_1, label_2, label_3] if l is not None]

            # convert scheduled for to date
            if scheduled_for is not None:
                scheduled_for = scheduled_for.strftime(current_app.config["RESPONSE_DATE_FORMAT"])

            tasks.append(
                {
                    "id": id_,
                    "type": type_,
                    "description": description,
                    "priority": priority,
                    "status": status,
                    "assignee": assignee,
                    "assignee_id": assignee_id,
                    "labels": labels,
                    "scheduled_for": scheduled_for,
                }
            )
        return {"tasks": tasks}, 200
