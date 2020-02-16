from flask import request
from flask_restx import Namespace, fields

from app.Controllers.Base import RequestValidationController
from app.Decorators import requires_jwt, authorize
from app.Extensions.Database import session_scope
from app.Models import TaskStatus, Task
from app.Models.Enums import TaskStatuses, Operations, Resources
from app.Models.RBAC import ServiceAccount
from app.Services import TaskService

api = Namespace(path="/task/transition", name="Task", description="Manage a task")

task_service = TaskService()


@api.route("/")
class TransitionTask(RequestValidationController):
    statuses = ["READY", "IN_PROGRESS", "COMPLETED"]
    request_dto = api.model(
        "Transition Task Request",
        {"task_id": fields.Integer(required=True), "task_status": fields.String(enum=statuses, required=True),},
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
            task = task_service.get(request_body["task_id"], request_body["org_id"])
            task_service.transition(task, request_body["task_status"])
        else:
            task = self.validate_transition_task(**kwargs)
            task_service.transition(task, request_body["task_status"], kwargs["req_user"])

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

        with session_scope() as session:
            tasks = session.query(Task).filter_by(org_id=req_user.org_id).all()

        # handle case where no-one is assigned to the task
        all_task_transitions = []
        for task in tasks:
            this_task_transitions = {"task_id": task.id, "valid_transitions": []}

            if task.assignee is None:
                # you can move from ready to ready, cancelled and dropped are not included because they are handled
                # separately
                valid_transitions = {
                    TaskStatuses.READY: [TaskStatuses.READY],
                    TaskStatuses.SCHEDULED: [TaskStatuses.READY],
                }

                # search list for querying db
                search = valid_transitions.get(task.status, [])

                with session_scope() as session:
                    # will return all the attributes for the ready status
                    enabled_qry = session.query(TaskStatus).filter(TaskStatus.status.in_(search)).all()

                # enabled options
                this_task_transitions["valid_transitions"] += [ts.status for ts in enabled_qry]

            else:
                # if someone is assigned to the task, then these are the available transitions
                valid_transitions = {
                    TaskStatuses.READY: [TaskStatuses.READY, TaskStatuses.IN_PROGRESS, TaskStatuses.CANCELLED],
                    TaskStatuses.IN_PROGRESS: [TaskStatuses.IN_PROGRESS, TaskStatuses.COMPLETED, TaskStatuses.DELAYED],
                    TaskStatuses.DELAYED: [TaskStatuses.DELAYED, TaskStatuses.IN_PROGRESS],
                    TaskStatuses.SCHEDULED: [TaskStatuses.READY],
                }

                # search list for querying db
                search = valid_transitions.get(task.status, [])

                with session_scope() as session:
                    # will return all attributes for the enabled tasks
                    enabled_qry = session.query(TaskStatus).filter(TaskStatus.status.in_(search)).all()

                # enabled options
                this_task_transitions["valid_transitions"] += [ts.status for ts in enabled_qry]

            all_task_transitions.append(this_task_transitions)

        return all_task_transitions, 200
