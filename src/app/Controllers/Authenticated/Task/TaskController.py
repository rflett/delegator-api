import datetime
import pytz

import structlog
from flask import request, current_app
from flask_restx import Namespace, fields
from sqlalchemy import exists, and_

from app.Controllers.Base import RequestValidationController
from app.Decorators import requires_jwt, authorize
from app.Extensions.Database import session_scope
from app.Extensions.Errors import ResourceNotFoundError, ValidationError
from app.Models import Event, Notification, NotificationAction
from app.Models.Dao import Task, User
from app.Models.Enums import Operations, Resources, Events, TaskStatuses
from app.Models.Enums.Notifications import ClickActions, TargetTypes
from app.Models.Enums.Notifications.NotificationIcons import NotificationIcons
from app.Utilities.All import get_all_user_ids, reindex_display_orders

api = Namespace(path="/task", name="Task", description="Manage a task")
log = structlog.getLogger()
task_statuses = ["SCHEDULED", "READY", "IN_PROGRESS", "COMPLETED", "CANCELLED"]


class NullableDateTime(fields.DateTime):
    __schema_type__ = ["string", "null"]
    __schema_example__ = "None|2019-09-17T19:08:00+10:00"


class NullableInteger(fields.Integer):
    __schema_type__ = ["integer", "null"]
    __schema_example__ = "nullable string"


class NullableString(fields.Integer):
    __schema_type__ = ["string", "null"]
    __schema_example__ = "nullable string"


@api.route("/<int:task_id>")
class GetTask(RequestValidationController):
    task_status_dto = api.model(
        "Task Status Dto",
        {
            "status": fields.String(enum=task_statuses),
            "label": fields.String(),
            "disabled": fields.Boolean(),
            "tooltip": fields.String(),
        },
    )
    user_dto = api.model(
        "Task User Dto",
        {"id": fields.Integer(), "uuid": fields.String(), "first_name": fields.String(), "last_name": fields.String()},
    )
    priority_dto = api.model("Task Priority Dto", {"priority": fields.Integer(min=0, max=2), "label": fields.String()})
    task_label_dto = api.model(
        "Task Label Dto", {"id": fields.Integer(), "label": fields.String(), "colour": fields.String()}
    )
    response_dto = api.model(
        "Get Task Response",
        {
            "id": fields.Integer(),
            "org_id": fields.Integer(),
            "title": fields.String(),
            "description": fields.String(),
            "status": fields.Nested(task_status_dto),
            "time_estimate": fields.Integer(),
            "scheduled_for": NullableDateTime,
            "scheduled_notification_period": fields.Integer(),
            "scheduled_notification_sent": NullableDateTime,
            "assignee": fields.Nested(user_dto, allow_null=True),
            "priority": fields.Nested(priority_dto),
            "created_by": fields.Nested(user_dto, allow_null=True),
            "created_at": fields.DateTime(),
            "started_at": NullableDateTime,
            "finished_by": fields.Nested(user_dto, allow_null=True),
            "finished_at": NullableDateTime,
            "status_changed_at": NullableDateTime,
            "priority_changed_at": NullableDateTime,
            "labels": fields.List(fields.Nested(task_label_dto)),
            "custom_1": fields.String(),
            "custom_2": fields.String(),
            "custom_3": fields.String(),
            "display_order": fields.Integer(),
        },
    )

    @requires_jwt
    @authorize(Operations.GET, Resources.TASK)
    @api.marshal_with(response_dto, code=200)
    def get(self, task_id: int, **kwargs):
        """Get a single task"""
        req_user: User = kwargs["req_user"]

        with session_scope() as session:
            # return 404 if task not found in org
            if not session.query(exists().where(and_(Task.id == task_id, Task.org_id == req_user.org_id))).scalar():
                raise ResourceNotFoundError(f"Task {task_id} doesn't exist")

            # the aliases are named so that it's easier to split on later
            qry = session.execute(
                """ SELECT t.id AS task_id,
                           t.org_id AS task_org_id,
                           t.title AS task_title,
                           t.description AS task_description,
                           t.time_estimate AS task_time_estimate,
                           t.scheduled_for AS task_scheduled_for,
                           t.scheduled_notification_period AS task_scheduled_notification_period,
                           t.scheduled_notification_sent AS task_scheduled_notification_sent,
                           t.created_at AS task_created_at,
                           t.started_at AS task_started_at,
                           t.finished_at AS task_finished_at,
                           t.status_changed_at AS task_status_changed_at,
                           t.priority_changed_at AS task_priority_changed_at,
                           t.custom_1 AS task_custom_1,
                           t.custom_2 AS task_custom_2,
                           t.custom_3 AS task_custom_3,
                           t.display_order AS task_display_order,
                           ts.status AS status_status,
                           ts.label AS status_label,
                           tp.priority AS priority_priority,
                           tp.label AS priority_label,
                           tl1.id AS label1_id,
                           tl1.label AS label1_label,
                           tl1.colour AS label1_colour,
                           tl2.id AS label2_id,
                           tl2.label AS label2_label,
                           tl2.colour AS label2_colour,
                           tl3.id AS label3_id,
                           tl3.label AS label3_label,
                           tl3.colour AS label3_colour,
                           ta.id AS assignee_id,
                           ta.first_name AS assignee_first_name,
                           ta.uuid AS assignee_uuid,
                           ta.last_name AS assignee_last_name,
                           tcb.id AS created_by_id,
                           tcb.first_name AS created_by_first_name,
                           tcb.last_name AS created_by_last_name,
                           tfb.id AS finished_by_id,
                           tfb.first_name AS finished_by_first_name,
                           tfb.last_name AS finished_by_last_name
                    FROM tasks t INNER JOIN task_statuses ts ON t.status = ts.status
                                 INNER JOIN task_priorities tp ON t.priority = tp.priority
                                 LEFT JOIN task_labels tl1 ON t.label_1 = tl1.id
                                 LEFT JOIN task_labels tl2 ON t.label_2 = tl2.id
                                 LEFT JOIN task_labels tl3 ON t.label_3 = tl3.id
                                 LEFT JOIN users ta ON t.assignee = ta.id
                                 LEFT JOIN users tcb ON t.created_by = tcb.id
                                 LEFT JOIN users tfb ON t.finished_by = tfb.id
                    WHERE t.id = :task_id
                    AND   t.org_id = :org_id
                """,
                {"task_id": task_id, "org_id": req_user.org_id},
            )

        result = dict(qry.fetchone().items())

        if result["assignee_id"] is None:
            assignee = None
        else:
            assignee = {
                "id": result["assignee_id"],
                "uuid": result["assignee_uuid"],
                "first_name": result["assignee_first_name"],
                "last_name": result["assignee_last_name"],
            }

        if result["created_by_id"] is None:
            created_by = None
        else:
            created_by = {
                "id": result["created_by_id"],
                "first_name": result["created_by_first_name"],
                "last_name": result["created_by_last_name"],
            }

        if result["finished_by_id"] is None:
            finished_by = None
        else:
            finished_by = {
                "id": result["finished_by_id"],
                "first_name": result["finished_by_first_name"],
                "last_name": result["finished_by_last_name"],
            }

        ret = {
            "status": {"status": result["status_status"], "label": result["status_label"]},
            "priority": {"priority": result["priority_priority"], "label": result["priority_label"]},
            "assignee": assignee,
            "created_by": created_by,
            "finished_by": finished_by,
            "labels": [],
        }

        for alias, value in result.items():
            if alias.startswith("task_"):
                ret[alias[len("task_") :]] = value

        # add the labels (at most 3)
        for i in range(1, 4):
            if result[f"label{i}_id"] is not None:
                ret["labels"].append(
                    {
                        "id": result[f"label{i}_id"],
                        "label": result[f"label{i}_label"],
                        "colour": result[f"label{i}_colour"],
                    }
                )

        # convert to correct time format
        for k, v in ret.items():
            if isinstance(v, datetime.datetime):
                ret[k] = pytz.utc.localize(v).strftime(current_app.config["RESPONSE_DATE_FORMAT"])

        req_user.log(Operations.GET, Resources.TASK, resource_id=task_id)
        return ret, 200


@api.route("/")
class ManageTask(RequestValidationController):
    update_task_dto = api.model(
        "Update Task Request",
        {
            "id": fields.Integer(required=True),
            "title": fields.String(required=True),
            "status": fields.String(enum=task_statuses, required=True),
            "assignee": NullableInteger(),
            "priority": fields.Integer(min=0, max=2, required=True),
            "labels": fields.List(fields.Integer(), max_items=3, required=True, min_items=0),
            "description": fields.String(),
            "time_estimate": fields.Integer(),
            "scheduled_for": NullableDateTime(),
            "scheduled_notification_period": fields.Integer(),
            "custom_1": NullableString(),
            "custom_2": NullableString(),
            "custom_3": NullableString(),
        },
    )

    @requires_jwt
    @authorize(Operations.UPDATE, Resources.TASK)
    @api.expect(update_task_dto, validate=True)
    @api.response(204, "Success")
    def put(self, **kwargs):
        """Update a task """
        req_user: User = kwargs["req_user"]
        request_body = request.get_json()

        # validate
        task_to_update = self.check_task_id(request_body["id"], kwargs["req_user"].org_id)
        self.check_task_assignee(request_body.get("assignee"), **kwargs),
        self.check_task_labels(request_body["labels"], kwargs["req_user"].org_id)

        # if the assignee isn't the same as before then assign someone to it, if the new assignee is null or
        # omitted from the request, then assign the task
        assignee = request_body.get("assignee")
        if task_to_update.assignee != assignee:
            if assignee is None:
                task_to_update.unassign(req_user)
            else:
                task_to_update.assign(
                    assignee=assignee,
                    req_user=req_user,
                    notify=False if task_to_update.status == TaskStatuses.SCHEDULED else True,
                )

        # transition
        task_status = request_body["status"]
        if task_to_update.status != task_status:
            task_to_update.transition(status=task_status, req_user=req_user)

        # change priority
        task_priority = request_body["priority"]
        if task_to_update.priority != task_priority:
            task_to_update.change_priority(priority=task_priority, notification_exclusions=[req_user.id])

        # rescheduling
        if task_to_update.status == TaskStatuses.SCHEDULED:
            if request_body.get("scheduled_for") is None or request_body.get("scheduled_notification_period") is None:
                raise ValidationError(
                    "Task is scheduled so scheduled_for and scheduled_notification_period are required"
                )
            with session_scope():
                task_to_update.scheduled_for = request_body.get("scheduled_for")
                task_to_update.scheduled_notification_period = request_body.get("scheduled_notification_period")
            # TODO do we want send task rescheduled notifications here?

        # update remaining attributes
        with session_scope():
            labels = self._get_labels(request_body["labels"])
            task_to_update.title = request_body["title"]
            task_to_update.label_1 = labels["label_1"]
            task_to_update.label_2 = labels["label_2"]
            task_to_update.label_3 = labels["label_3"]
            task_to_update.custom_1 = request_body.get("custom_1")
            task_to_update.custom_2 = request_body.get("custom_2")
            task_to_update.custom_3 = request_body.get("custom_3")

            if request_body.get("description") is not None:
                task_to_update.description = request_body["description"]
            if request_body.get("time_estimate") is not None:
                task_to_update.time_estimate = request_body["time_estimate"]

        # publish event
        Event(
            org_id=task_to_update.org_id,
            event=Events.task_updated,
            event_id=task_to_update.id,
            event_friendly=f"Updated by {req_user.name()}.",
        ).publish()

        req_user.log(Operations.UPDATE, Resources.TASK, resource_id=task_to_update.id)
        return "", 204

    create_task_dto = api.model(
        "Create Task Request",
        {
            "title": fields.String(required=True),
            "template_id": NullableInteger(),
            "priority": fields.Integer(min=0, max=2, required=True),
            "description": NullableString(),
            "time_estimate": NullableInteger(),
            "scheduled_for": NullableDateTime(),
            "scheduled_notification_period": NullableInteger(),
            "assignee": NullableInteger(),
            "labels": fields.List(fields.Integer(), max_items=3),
            "custom_1": NullableString(),
            "custom_2": NullableString(),
            "custom_3": NullableString(),
        },
    )

    @requires_jwt
    @authorize(Operations.CREATE, Resources.TASK)
    @api.expect(create_task_dto, validate=True)
    @api.response(204, "Success")
    def post(self, **kwargs):
        """Creates a task"""
        req_user: User = kwargs["req_user"]
        request_body = request.get_json()

        self.check_task_template_id(request_body.get("template_id"))
        self.check_task_assignee(request_body.get("assignee"), **kwargs)
        self.check_task_labels(request_body.get("labels", []), req_user.org_id)

        reindex_display_orders(req_user.org_id)

        with session_scope():
            task = Task(
                org_id=req_user.org_id,
                title=request_body["title"],
                template_id=request_body.get("template_id"),
                description=request_body.get("description"),
                time_estimate=request_body.get("time_estimate"),
                priority=request_body["priority"],
                created_by=req_user.id,
                custom_1=request_body.get("custom_1"),
                custom_2=request_body.get("custom_2"),
                custom_3=request_body.get("custom_3"),
                **self._get_labels(request_body.get("labels", [])),
            )

        if request_body.get("scheduled_for") is not None:
            self._schedule_task(req_user, task)
        else:
            self._create_task(req_user, task)

        return "", 204

    @staticmethod
    def _create_task(req_user: User, task: Task):
        """Creates a new task"""
        request_body = request.get_json()
        with session_scope() as session:
            task.status = TaskStatuses.READY
            session.add(task)

        Event(
            org_id=task.org_id,
            event=Events.task_created,
            event_id=task.id,
            event_friendly=f"Created by {req_user.name()}.",
        ).publish()
        Event(
            org_id=req_user.org_id,
            event=Events.user_created_task,
            event_id=req_user.id,
            event_friendly=f"Created task {task.title}.",
        ).publish()
        req_user.log(Operations.CREATE, Resources.TASK, resource_id=task.id)
        log.info(f"created task {task.id}")

        # optionally assign the task if an assignee was present in the create task request
        if request_body.get("assignee") is not None:
            task.assign(assignee=request_body["assignee"], req_user=req_user)
        else:
            created_notification = Notification(
                title="Task created",
                event_name=Events.task_created,
                msg=f"{task.title} task has been created.",
                target_type=TargetTypes.TASK,
                target_id=task.id,
                actions=[NotificationAction(ClickActions.ASSIGN_TO_ME, NotificationIcons.ASSIGN_TO_ME_ICON)],
                user_ids=get_all_user_ids(req_user.org_id, exclude=[req_user.id]),
            )
            created_notification.push()

    @staticmethod
    def _schedule_task(req_user: User, task: Task):
        """Schedules a new task"""
        request_body = request.get_json()
        with session_scope() as session:
            task.status = TaskStatuses.SCHEDULED
            task.scheduled_for = request_body["scheduled_for"]
            task.scheduled_notification_period = request_body.get("scheduled_notification_period")
            session.add(task)

        Event(
            org_id=task.org_id,
            event=Events.task_scheduled,
            event_id=task.id,
            event_friendly=f"Scheduled by {req_user.name()}.",
        ).publish()
        Event(
            org_id=req_user.org_id,
            event=Events.user_scheduled_task,
            event_id=req_user.id,
            event_friendly=f"Scheduled task {task.title}.",
        ).publish()
        req_user.log(Operations.CREATE, Resources.TASK, resource_id=task.id)
        log.info(f"Scheduled task {task.id}")

        # optionally assign the task if an assignee was present in the create task request
        if request_body.get("assignee") is not None:
            task.assign(assignee=request_body.get("assignee"), req_user=req_user, notify=False)

    @staticmethod
    def _get_labels(label_attrs: dict) -> dict:
        """labels provided as a list, so map their index to the Task column"""
        labels = {"label_1": None, "label_2": None, "label_3": None}
        for i in range(1, len(label_attrs) + 1):
            labels[f"label_{i}"] = label_attrs[i - 1]
        return labels
