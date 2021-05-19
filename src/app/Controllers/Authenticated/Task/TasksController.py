import datetime
import pytz

import structlog
from flask import current_app, request
from flask_restx import Namespace, fields
from sqlalchemy import or_, func, cast, Date
from sqlalchemy.orm import aliased

from app.Controllers.Base import RequestValidationController
from app.Decorators import requires_jwt, authorize
from app.Extensions.Database import session_scope
from app.Extensions.Errors import ValidationError
from app.Models import GetTasksFilters, GetTasksFiltersSchema, get_tasks_schema_docs
from app.Models.Dao import User, Task, TaskLabel, TaskStatus, DelayedTask, TaskPriority
from app.Models.Enums import Operations, Resources, TaskStatuses
from app.Utilities.All import format_date

api = Namespace(path="/tasks", name="Tasks", description="Manage tasks")
log = structlog.getLogger()


class NullableDateTime(fields.DateTime):
    __schema_type__ = ["string", "null"]
    __schema_example__ = "None|2019-09-17T19:08:00+10:00"


class NullableString(fields.Integer):
    __schema_type__ = ["string", "null"]
    __schema_example__ = "nullable string"


class NullableInteger(fields.Integer):
    __schema_type__ = ["integer", "null"]
    __schema_example__ = "nullable string"


class NullableList(fields.Integer):
    __schema_type__ = ["list", "null"]
    __schema_example__ = "nullable list"


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
    @api.doc(params=get_tasks_schema_docs)
    @api.marshal_with(response_dto, code=200)
    def get(self, **kwargs):
        """Get all tasks"""
        req_user = kwargs["req_user"]

        # validate the filtering arguments
        arg_errors = GetTasksFiltersSchema().validate(request.args)
        if arg_errors:
            raise ValidationError(arg_errors)

        task_filters = GetTasksFilters(request.args)
        log.info("Parsed request filters", filters=task_filters)

        with session_scope() as session:
            label1, label2, label3 = aliased(TaskLabel), aliased(TaskLabel), aliased(TaskLabel)

            filters = task_filters.filters(req_user.org_id, label1, label2, label3)

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
                .filter(*filters)
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

        log.info(f"Found {len(tasks)} tasks matching filters")
        return {"tasks": tasks}, 200


@api.route("/completed")
class CompletedTasks(RequestValidationController):
    # request
    filters = api.model(
        "Completed Task Filters Dto",
        {
            "status": NullableString(enum=[TaskStatuses.COMPLETED, TaskStatuses.CANCELLED]),
            "assignee": NullableInteger(),
            "labels": fields.List(fields.Integer(), min_items=0),
        },
    )
    request_dto = api.model(
        "Completed Tasks Request Dto",
        {
            "page_index": fields.Integer(required=True, min=0),
            "page_size": fields.Integer(required=True, min=0, max=50),
            "sort_by": fields.String(required=True, enum=["finishedAt"]),
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
    @api.expect(request_dto, validate=True)
    @api.marshal_with(response_dto, code=200)
    def post(self, **kwargs):
        """Get all completed tasks"""
        req_user = kwargs["req_user"]
        request_body = request.get_json()

        log.info("Getting completed tasks with filters", **request_body)

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
                    assignee.id,
                    assignee.first_name,
                    assignee.last_name,
                    created_by.id,
                    created_by.first_name,
                    created_by.last_name,
                    finished_by.id,
                    finished_by.first_name,
                    finished_by.last_name,
                    label1,
                    label2,
                    label3,
                )
                .select_from(Task)
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
            log.info(f"Found {count} completed tasks to sort and paginate")

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
                assignee_id,
                assignee_first_name,
                assignee_last_name,
                created_by_id,
                created_by_first_name,
                created_by_last_name,
                finished_by_id,
                finished_by_first_name,
                finished_by_last_name,
                label_1,
                label_2,
                label_3,
            ) = task

            # calc time to finish
            if started_at is None:
                time_to_finish_min = 0
            else:
                time_to_finish_date = finished_at - started_at
                time_to_finish_min = time_to_finish_date.total_seconds() // 60

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
                    "assignee": {
                        "id": assignee_id,
                        "first_name": assignee_first_name,
                        "last_name": assignee_last_name,
                    },
                    "created_by": {
                        "id": created_by_id,
                        "first_name": created_by_first_name,
                        "last_name": created_by_last_name,
                    },
                    "finished_by": {
                        "id": finished_by_id,
                        "first_name": finished_by_first_name,
                        "last_name": finished_by_last_name,
                    },
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
            time_spent_delayed += (expired - delayed_at).total_seconds()

        # return as minutes
        return time_spent_delayed // 60


@api.route("/scheduled")
class ScheduledTasks(RequestValidationController):
    # request
    request_dto = api.model(
        "ScheduledTasksRequestDto", {"start_date": fields.Date(required=True), "end_date": fields.Date(required=True)}
    )

    # response
    priority_dto = api.model("Task Priority Dto", {"priority": fields.Integer(min=0, max=2), "label": fields.String()})
    task_dto = api.model(
        "ScheduledTasksTaskDto",
        {
            "id": fields.Integer(),
            "title": fields.String(),
            "priority": fields.Nested(priority_dto),
            "start": fields.DateTime(),
            "end": NullableDateTime(),
        },
    )
    response_dto = api.model("ScheduledTasksResponseDto", {"tasks": fields.List(fields.Nested(task_dto))})

    @requires_jwt
    @authorize(Operations.GET, Resources.TASKS)
    @api.expect(request_dto, validate=True)
    @api.marshal_with(response_dto, code=200)
    def post(self, **kwargs):
        """Get all scheduled tasks"""
        req_user: User = kwargs["req_user"]
        request_body = request.get_json()

        try:
            start_year, start_month, start_day = request_body["start_date"].split("-")
            end_year, end_month, end_day = request_body["end_date"].split("-")
        except ValueError:
            raise ValidationError("start_date and end_date must be in format YYYY-MM-DD")

        try:
            start_date = datetime.date(int(start_year), int(start_month), int(start_day))
            end_date = datetime.date(int(end_year), int(end_month), int(end_day))
        except ValueError:
            raise ValidationError("start_date and end_date must be valid dates")

        if start_date > end_date:
            raise ValidationError("end_date must be after start_date")

        with session_scope() as session:
            qry = (
                session.query(Task.id, Task.title, TaskPriority, Task.scheduled_for, Task.time_estimate)
                .join(TaskPriority, Task.priority == TaskPriority.priority)
                .filter(
                    Task.org_id == req_user.org_id,
                    Task.status == TaskStatuses.SCHEDULED,
                    cast(Task.scheduled_for, Date) <= end_date,
                    cast(Task.scheduled_for, Date) >= start_date,
                )
                .all()
            )

        tasks = []

        for task in qry:
            id_, title, priority, scheduled_for, time_estimate = task

            if time_estimate > 0:
                end = scheduled_for + datetime.timedelta(seconds=time_estimate)
            else:
                end = None

            tasks.append(
                {
                    "id": id_,
                    "title": title,
                    "priority": priority.as_dict(),
                    "start": format_date(scheduled_for),
                    "end": format_date(end),
                }
            )

        return {"tasks": tasks}, 200
