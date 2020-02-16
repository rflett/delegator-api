from flask import request, current_app
from flask_restx import Namespace, fields
from sqlalchemy import exists, and_

from app.Controllers.Base import RequestValidationController
from app.Decorators import requires_jwt, authorize
from app.Extensions.Database import session_scope
from app.Extensions.Errors import ResourceNotFoundError
from app.Models import Activity, Notification
from app.Models.Dao import Task, User
from app.Models.Enums import Operations, Resources, Events, TaskStatuses, ClickActions
from app.Services import TaskService, UserService

api = Namespace(path="/task", name="Task", description="Manage a task")

task_service = TaskService()
user_service = UserService()

task_statuses = ["SCHEDULED", "READY", "IN_PROGRESS", "DELAYED", "COMPLETED", "CANCELLED"]


class NullableDateTime(fields.DateTime):
    __schema_type__ = ["datetime", "null"]
    __schema_example__ = "None|2019-09-17T19:08:00+10:00"


@api.route("/<int:task_id>")
class GetTask(RequestValidationController):

    task_type_dto = api.model(
        "Task Type Dto",
        {"id": fields.Integer(), "label": fields.String(), "disabled": NullableDateTime, "tooltip": fields.String()},
    )
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
        "Task User Dto", {"id": fields.Integer(), "first_name": fields.String(), "last_name": fields.String()},
    )
    priority_dto = api.model("Task Priority Dto", {"priority": fields.Integer(min=0, max=1), "label": fields.String()})
    task_label_dto = api.model(
        "Task Label Dto", {"id": fields.Integer(), "label": fields.String(), "colour": fields.String()}
    )
    response_dto = api.model(
        "Get Task Response",
        {
            "id": fields.Integer(),
            "org_id": fields.Integer(),
            "type": fields.Nested(task_type_dto),
            "description": fields.String(),
            "status": fields.Nested(task_status_dto),
            "time_estimate": fields.String(),
            "scheduled_for": NullableDateTime,
            "scheduled_notification_period": fields.Integer(),
            "scheduled_notification_sent": NullableDateTime,
            "assignee": fields.Nested(user_dto),
            "priority": fields.Nested(priority_dto),
            "created_by": fields.Nested(user_dto),
            "created_at": fields.DateTime(),
            "started_at": NullableDateTime,
            "finished_by": fields.Nested(user_dto),
            "finished_at": NullableDateTime,
            "status_changed_at": NullableDateTime,
            "priority_changed_at": NullableDateTime,
            "labels": fields.List(fields.Nested(task_label_dto)),
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
                           tt.id AS type_id,
                           tt.label AS type_label,
                           tt.disabled AS type_disabled,
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
                           ta.last_name AS assignee_last_name,
                           tcb.id AS created_by_id,
                           tcb.first_name AS created_by_first_name,
                           tcb.last_name AS created_by_last_name,
                           tfb.id AS finished_by_id,
                           tfb.first_name AS finished_by_first_name,
                           tfb.last_name AS finished_by_last_name
                    FROM tasks t INNER JOIN task_types tt ON t.type = tt.id
                                 INNER JOIN task_statuses ts ON t.status = ts.status
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

        ret = {
            "type": {"id": result["type_id"], "label": result["type_label"], "disabled": result["type_disabled"]},
            "status": {"status": result["status_status"], "label": result["status_label"]},
            "priority": {"priority": result["priority_priority"], "label": result["priority_label"]},
            "assignee": {
                "id": result["assignee_id"],
                "first_name": result["assignee_first_name"],
                "last_name": result["assignee_last_name"],
            },
            "created_by": {
                "id": result["created_by_id"],
                "first_name": result["created_by_first_name"],
                "last_name": result["created_by_last_name"],
            },
            "finished_by": {
                "id": result["finished_by_id"],
                "first_name": result["finished_by_first_name"],
                "last_name": result["finished_by_last_name"],
            },
            "labels": [],
        }

        # add task attributes to top level of ret dict
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

        req_user.log(operation=Operations.GET, resource=Resources.TASK, resource_id=task_id)
        return ret, 200


@api.route("/")
class ManageTask(RequestValidationController):

    update_task_dto = api.model(
        "Update Task Request",
        {
            "id": fields.Integer(required=True),
            "type_id": fields.Integer(required=True),
            "status": fields.String(enum=task_statuses, required=True),
            "assignee": fields.Integer(),
            "priority": fields.Integer(min=0, max=2, required=True),
            "labels": fields.List(fields.Integer(), max_items=3, required=True, min_items=0),
            "description": fields.String(),
            "time_estimate": fields.Integer(),
            "scheduled_for": NullableDateTime(),
            "scheduled_notification_period": fields.Integer(),
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
        self.check_task_status(request_body["status"]),
        self.check_task_assignee(request_body.get("assignee"), **kwargs),
        self.check_task_priority(request_body["priority"]),
        self.check_task_labels(request_body["labels"], kwargs["req_user"].org_id)

        # if the assignee isn't the same as before then assign someone to it, if the new assignee is null or
        # omitted from the request, then assign the task
        assignee = request_body.get("assignee")
        if task_to_update.assignee != assignee:
            if assignee is None:
                task_service.unassign(task=task_to_update, req_user=req_user)
            else:
                task_service.assign(
                    task=task_to_update,
                    assignee=assignee,
                    req_user=req_user,
                    notify=False if task_to_update.status == TaskStatuses.SCHEDULED else True,
                )

        # transition
        task_status = request_body["status"]
        if task_to_update.status != task_status:
            task_service.transition(task=task_to_update, status=task_status, req_user=req_user)

        # change priority
        task_priority = request_body["priority"]
        if task_to_update.priority != task_priority:
            task_service.change_priority(task=task_to_update, priority=task_priority)

        # don't update scheduled info if it wasn't scheduled to begin with, or the notification has been sent
        if (
            task_to_update.scheduled_for is None
            and task_to_update.scheduled_notification_period is None
            or task_to_update.scheduled_notification_sent
        ):
            with session_scope():
                task_to_update.scheduled_for = request_body.get("scheduled_for")
                task_to_update.scheduled_notification_period = request_body.get("scheduled_notification_period")

        # update remaining attributes
        with session_scope():
            labels = self._get_labels(request_body["labels"])
            task_to_update.label_1 = labels["label_1"]
            task_to_update.label_2 = labels["label_3"]
            task_to_update.label_3 = labels["label_3"]

            if request_body.get("description") is not None:
                task_to_update.description = request_body["description"]
            if request_body.get("time_estimate") is not None:
                task_to_update.time_estimate = request_body["time_estimate"]

        # publish event
        Activity(
            org_id=task_to_update.org_id,
            event=Events.task_updated,
            event_id=task_to_update.id,
            event_friendly=f"Updated by {req_user.name()}.",
        ).publish()

        req_user.log(operation=Operations.UPDATE, resource=Resources.TASK, resource_id=task_to_update.id)
        return "", 204

    create_task_dto = api.model(
        "Create Task Request",
        {
            "type_id": fields.Integer(required=True),
            "priority": fields.Integer(min=0, max=2, required=True),
            "description": fields.String(),
            "time_estimate": fields.Integer(),
            "scheduled_for": NullableDateTime(),
            "scheduled_notification_period": fields.Integer(),
            "assignee": fields.Integer(),
            "labels": fields.List(fields.Integer(), max_items=3),
        },
    )

    @requires_jwt
    @authorize(Operations.CREATE, Resources.TASK)
    @api.expect(create_task_dto)
    @api.response(204, "Success")
    def post(self, **kwargs):
        """Creates a task"""
        req_user: User = kwargs["req_user"]
        request_body = request.get_json()

        self.check_task_type_id(request_body["type_id"])
        self.check_task_priority(request_body["priority"])
        self.check_task_assignee(request_body.get("assignee"), **kwargs)
        self.check_task_labels(request_body.get("labels", []), req_user.org_id)

        if (
            request_body.get("scheduled_for") is not None
            and request_body.get("scheduled_notification_period") is not None
        ):
            self._schedule_task(req_user)
        else:
            self._create_task(req_user)

        return "", 204

    def _create_task(self, req_user: User):
        """Creates a new task"""
        request_body = request.get_json()
        with session_scope() as session:
            task = Task(
                org_id=req_user.org_id,
                type=request_body["type_id"],
                description=request_body.get("description"),
                status=TaskStatuses.READY,
                time_estimate=request_body.get("time_estimate"),
                priority=request_body["priority"],
                created_by=req_user.id,
                **self._get_labels(request_body.get("labels", [])),
            )
            session.add(task)

        Activity(
            org_id=task.org_id,
            event=Events.task_created,
            event_id=task.id,
            event_friendly=f"Created by {req_user.name()}.",
        ).publish()
        Activity(
            org_id=req_user.org_id,
            event=Events.user_created_task,
            event_id=req_user.id,
            event_friendly=f"Created task {task.label()}.",
        ).publish()
        req_user.log(operation=Operations.CREATE, resource=Resources.TASK, resource_id=task.id)
        current_app.logger.info(f"created task {task.id}")

        # optionally assign the task if an assignee was present in the create task request
        if request_body.get("assignee") is not None:
            task_service.assign(task=task, assignee=request_body["assignee"], req_user=req_user)
        else:
            created_notification = Notification(
                title="Task created",
                event_name=Events.task_created,
                msg=f"{task.label()} task has been created.",
                click_action=ClickActions.ASSIGN_TO_ME,
                task_action_id=task.id,
                user_ids=user_service.get_all_user_ids(req_user.org_id),
            )
            created_notification.push()

    def _schedule_task(self, req_user: User):
        """Schedules a new task"""
        request_body = request.get_json()
        with session_scope() as session:
            task = Task(
                org_id=req_user.org_id,
                type=request_body["type_id"],
                description=request_body.get("description"),
                status=TaskStatuses.SCHEDULED,
                scheduled_for=request_body["scheduled_for"],
                scheduled_notification_period=request_body["scheduled_notification_period"],
                time_estimate=request_body.get("time_estimate"),
                priority=request_body["priority"],
                created_by=req_user.id,
                **self._get_labels(request_body.get("labels", [])),
            )
            session.add(task)

        Activity(
            org_id=task.org_id,
            event=Events.task_scheduled,
            event_id=task.id,
            event_friendly=f"Scheduled by {req_user.name()}.",
        ).publish()
        Activity(
            org_id=req_user.org_id,
            event=Events.user_scheduled_task,
            event_id=req_user.id,
            event_friendly=f"Scheduled task {task.label()}.",
        ).publish()
        req_user.log(operation=Operations.CREATE, resource=Resources.TASK, resource_id=task.id)
        current_app.logger.info(f"Scheduled task {task.id}")

        # optionally assign the task if an assignee was present in the create task request
        if request_body.get("assignee") is not None:
            task_service.assign(task=task, assignee=request_body.get("assignee"), req_user=req_user, notify=False)

    @staticmethod
    def _get_labels(label_attrs: dict) -> dict:
        """labels provided as a list, so map their index to the Task column"""
        labels = {"label_1": None, "label_2": None, "label_3": None}
        for i in range(1, len(label_attrs) + 1):
            labels[f"label_{i}"] = label_attrs[i - 1]
        return labels
