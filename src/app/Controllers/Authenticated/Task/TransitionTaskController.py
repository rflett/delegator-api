from flask import request
from flask_restx import Namespace, fields

import structlog
from sqlalchemy.orm import aliased

from app.Controllers.Base import RequestValidationController
from app.Decorators import requires_jwt, authorize
from app.Extensions.Database import session_scope
from app.Extensions.Errors import ValidationError
from app.Models import GetTasksFilters, GetTasksFiltersSchema
from app.Models.Dao import TaskLabel, Task
from app.Models.Enums import TaskStatuses, Operations, Resources
from app.Models.RBAC import ServiceAccount
from app.Utilities.All import reindex_display_orders, get_task_by_id

api = Namespace(path="/task/transition", name="Task", description="Manage a task")
log = structlog.getLogger()


@api.route("/")
class TransitionTask(RequestValidationController):
    statuses = ["READY", "IN_PROGRESS", "COMPLETED", "CANCELLED"]
    request_dto = api.model(
        "Transition Task Request",
        {
            "task_id": fields.Integer(required=True),
            "task_status": fields.String(enum=statuses, required=True),
            "display_order": fields.Integer(min=0),
        },
    )

    @requires_jwt
    @authorize(Operations.TRANSITION, Resources.TASK)
    @api.expect(request_dto, validate=True)
    @api.response(204, "Success")
    def put(self, **kwargs):
        """Transitions a task to another status"""
        req_user = kwargs["req_user"]
        request_body = request.get_json()

        if isinstance(req_user, ServiceAccount):
            task = get_task_by_id(request_body["task_id"], request_body["org_id"])
            task.transition(request_body["task_status"])
        else:
            task = self.validate_transition_task(**kwargs)
            task.transition(request_body["task_status"], kwargs["req_user"])

        # update the display order
        display_order = request_body.get("display_order", 0)
        reindex_display_orders(task.org_id, new_position=display_order)
        with session_scope():
            task.display_order = display_order

        return "", 204

    task_transition_dto = api.model(
        "Get Task Transitions Dto",
        {"task_id": fields.Integer(), "valid_transitions": fields.List(fields.String(enum=statuses))},
    )

    @requires_jwt
    @authorize(Operations.GET, Resources.TASK_TRANSITIONS)
    @api.marshal_with(task_transition_dto, code=200)
    def get(self, **kwargs):
        """Returns all tasks and the statuses they can be transitioned to"""
        req_user = kwargs["req_user"]

        # validate the filtering arguments
        arg_errors = GetTasksFiltersSchema().validate(request.args)
        if arg_errors:
            raise ValidationError(arg_errors)

        task_filters = GetTasksFilters(request.args)
        log.info("Parsed request filters", filters=task_filters)

        valid_unassigned_transitions = {
            TaskStatuses.READY: [TaskStatuses.READY],
            TaskStatuses.SCHEDULED: [TaskStatuses.READY],
        }
        valid_assigned_transitions = {
            TaskStatuses.READY: [TaskStatuses.READY, TaskStatuses.IN_PROGRESS, TaskStatuses.CANCELLED],
            TaskStatuses.IN_PROGRESS: [
                TaskStatuses.IN_PROGRESS,
                TaskStatuses.DELAYED,
                TaskStatuses.COMPLETED,
                TaskStatuses.CANCELLED,
            ],
            TaskStatuses.DELAYED: [TaskStatuses.DELAYED, TaskStatuses.IN_PROGRESS],
            TaskStatuses.SCHEDULED: [TaskStatuses.READY],
        }

        with session_scope() as session:
            label1, label2, label3 = aliased(TaskLabel), aliased(TaskLabel), aliased(TaskLabel)
            filters = task_filters.filters(req_user.org_id, label1, label2, label3)
            tasks = session.query(Task.id, Task.status, Task.assignee).filter(*filters).all()

        # handle case where no-one is assigned to the task
        all_task_transitions = []
        for task_id, task_status, task_assignee in tasks:
            this_task_transitions = {"task_id": task_id, "valid_transitions": []}

            if task_assignee is None:
                this_task_transitions["valid_transitions"] += valid_unassigned_transitions.get(task_status, [])
            else:
                this_task_transitions["valid_transitions"] += valid_assigned_transitions.get(task_status, [])

            all_task_transitions.append(this_task_transitions)

        return all_task_transitions, 200
