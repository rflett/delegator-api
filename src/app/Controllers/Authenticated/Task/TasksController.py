import datetime
import pytz
from dateutil import tz

from flask import current_app, request
from flask_restx import Namespace, fields
from sqlalchemy import and_, or_, func
from sqlalchemy.orm import aliased

from app.Controllers.Base import RequestValidationController
from app.Decorators import requires_jwt, authorize
from app.Extensions.Database import session_scope
from app.Models.Dao import User, Task, TaskLabel, TaskStatus, DelayedTask
from app.Models.Enums import Operations, Resources, TaskStatuses
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


@api.route("/completed")
class CompletedTasks(RequestValidationController):
    # request
    filters = api.model(
        "Completed Task Filters Dto",
        {
            "status": fields.String(enum=[TaskStatuses.COMPLETED, TaskStatuses.CANCELLED]),
            "assignee": fields.Integer(),
            "labels": fields.List(fields.Integer()),
        },
    )
    request_dto = api.model(
        "Completed Tasks Request Dto",
        {
            "page_index": fields.Integer(required=True, min=0),
            "page_size": fields.Integer(required=True, min=0),
            "sort_by": fields.String(required=True, enum=["finishedAt", "timeToFinish", "timeSpentDelayed"]),
            "sort_direction": fields.String(required=True, enum=["asc", "desc"]),
            "filters": fields.Nested(filters, required=True),
        },
    )
    # response
    user_dto = api.model(
        "Task User Dto",
        {"id": fields.Integer(), "uuid": fields.String(), "first_name": fields.String(), "last_name": fields.String()},
    )
    task_label_dto = api.model(
        "Task Label Dto", {"id": fields.Integer(), "label": fields.String(), "colour": fields.String()}
    )
    task_status_dto = api.model(
        "Task Status Dto",
        {
            "status": fields.String(enum=[TaskStatuses.COMPLETED, TaskStatuses.CANCELLED]),
            "label": fields.String(),
            "disabled": fields.Boolean(),
            "tooltip": fields.String(),
        },
    )
    completed_task_dto = api.model(
        "Completed Task Dto",
        {
            "id": fields.Integer(),
            "title": fields.String(),
            "assignee": fields.Nested(user_dto),
            "created_by": fields.Nested(user_dto),
            "finished_by": fields.Nested(user_dto),
            "finished_at": fields.DateTime(),
            "status": fields.Nested(task_status_dto),
            "labels": fields.List(fields.Nested(task_label_dto)),
            "time_to_finish": fields.Integer(),
            "time_spent_delayed": fields.Integer(),
        },
    )
    response_dto = api.model(
        "Completed Tasks Response",
        {"count": fields.Integer(), "tasks": fields.List(fields.Nested(completed_task_dto))},
    )

    @requires_jwt
    @authorize(Operations.GET, Resources.TASKS)
    @api.expect(request_dto)
    @api.marshal_with(response_dto, code=200)
    def post(self, **kwargs):
        """Get all completed tasks"""
        req_user = kwargs["req_user"]
        request_body = request.get_json()

        with session_scope() as session:
            label1, label2, label3 = aliased(TaskLabel), aliased(TaskLabel), aliased(TaskLabel)
            assignee, created_by, finished_by = aliased(User), aliased(User), aliased(User)

            # do some filtering
            filters = [Task.org_id == req_user.org_id]

            # filter by status
            if request_body["filters"].get("status") is None:
                status_filter = [TaskStatuses.COMPLETED, TaskStatuses.CANCELLED]
            else:
                status_filter = [request_body["filters"]["status"]]

            filters.append(TaskStatus.status.in_(status_filter))

            # filter by assignee
            assignee_filter = request_body["filters"].get("assignee")
            if assignee_filter is not None:
                filters.append(assignee.id == assignee_filter)

            # filter by labels
            label_filter = request_body["filters"].get("labels")
            if label_filter is not None:
                for label_id in label_filter:
                    filters.append(or_(label1.id == label_id, label2.id == label_id, label3.id == label_id))

            qry = (
                session.query(
                    Task.id,
                    Task.title,
                    Task.started_at,
                    Task.finished_at,
                    TaskStatus,
                    assignee,
                    created_by,
                    finished_by,
                    label1,
                    label2,
                    label3,
                )
                .join(TaskStatus, TaskStatus.status == Task.status)
                .outerjoin(assignee, assignee.id == Task.assignee)
                .outerjoin(created_by, created_by.id == Task.created_by)
                .outerjoin(finished_by, finished_by.id == Task.finished_by)
                .outerjoin(label1, label1.id == Task.label_1)
                .outerjoin(label2, label2.id == Task.label_2)
                .outerjoin(label3, label3.id == Task.label_3)
                .filter(*filters)
            )

            # work out count efficiently
            count_qry = qry.statement.with_only_columns([func.count()]).order_by(None)
            count = qry.session.execute(count_qry).scalar()

            # we can sort by finished_at in this query
            if request_body["sort_by"] == "finishedAt" and request_body["sort_direction"] == "desc":
                ordering = Task.finished_at.desc()
            elif request_body["sort_by"] == "finishedAt" and request_body["sort_direction"] == "asc":
                ordering = Task.finished_at
            else:
                ordering = None

            # handle query pagination
            task_paginator = qry.order_by(ordering).paginate(
                page=request_body["page_index"] + 1,  # frontend paginating is 0-based, this is 1-based,
                per_page=request_body["page_size"],
            )

        tasks = []

        for task in task_paginator.items:
            (
                id_,
                title,
                started_at,
                finished_at,
                status,
                assignee,
                created_by,
                finished_by,
                label_1,
                label_2,
                label_3,
            ) = task

            # calc time to finish
            if started_at is None:
                time_to_finish_min = 0
            else:
                time_to_finish_date = finished_at - started_at
                time_to_finish_min = time_to_finish_date.seconds // 60

            # convert labels to a list
            labels = [label.as_dict() for label in [label_1, label_2, label_3] if label is not None]

            finished_at = pytz.utc.localize(finished_at)
            finished_at = finished_at.strftime(current_app.config["RESPONSE_DATE_FORMAT"])

            tasks.append(
                {
                    "id": id_,
                    "title": title,
                    "finished_at": finished_at,
                    "status": status.as_dict(),
                    "assignee": assignee.as_dict(),
                    "created_by": created_by.as_dict(),
                    "finished_by": finished_by.as_dict(),
                    "labels": labels,
                    "time_to_finish": time_to_finish_min,
                    "time_spent_delayed": self._calc_time_spent_delayed(id_),
                }
            )

        # we need to sort by time_to_finish or time_spent_delayed in place
        if request_body["sort_by"] == "timeToFinish":
            tasks.sort(key=lambda x: x["time_to_finish"], reverse=(request_body["sort_direction"] == "desc"))
        elif request_body["sort_by"] == "timeSpentDelayed":
            tasks.sort(key=lambda x: x["time_spent_delayed"], reverse=(request_body["sort_direction"] == "desc"))

        return {"count": count, "tasks": tasks}, 200

    @staticmethod
    def _calc_time_spent_delayed(task_id: int) -> int:
        """Calculate how long a task was spent delayed"""
        time_spent_delayed = 0

        with session_scope() as session:
            qry = (
                session.query(DelayedTask.delayed_at, DelayedTask.expired)
                .filter(DelayedTask.task_id == task_id, DelayedTask.expired != None)  # noqa
                .all()
            )

        for task in qry:
            delayed_at, expired = task
            # get the seconds it was delayed for
            time_spent_delayed += (expired - delayed_at).seconds

        # return as minutes
        return time_spent_delayed // 60
