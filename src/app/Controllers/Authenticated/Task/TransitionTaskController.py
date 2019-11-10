from flask import request, Response
from flask_restplus import Namespace

from app import session_scope
from app.Controllers.Base import RequestValidationController
from app.Decorators import requires_jwt, handle_exceptions, authorize, requires_token_auth
from app.Models import TaskStatus
from app.Models.Enums import TaskStatuses, Operations, Resources
from app.Models.Request import transition_task_request
from app.Models.Response import task_response, message_response_dto, task_statuses_response
from app.Services import TaskService

transition_task_route = Namespace(
    path="/task/transition",
    name="Task",
    description="Manage a task"
)

task_service = TaskService()


@transition_task_route.route("/")
class TransitionTask(RequestValidationController):

    @handle_exceptions
    @requires_jwt
    @authorize(Operations.TRANSITION, Resources.TASK)
    @transition_task_route.expect(transition_task_request)
    @transition_task_route.response(200, "Success", task_response)
    @transition_task_route.response(400, "Failed to transition the task", message_response_dto)
    def put(self, **kwargs) -> Response:
        """Transitions a task to another status"""
        task, task_status = self.validate_transition_task(request.get_json(), **kwargs)
        return self.ok(self._transition_task(task, task_status, kwargs['req_user']))

    @handle_exceptions
    @requires_token_auth
    @transition_task_route.expect(transition_task_request)
    @transition_task_route.response(200, "Success", task_response)
    @transition_task_route.response(400, "Failed to transition the task", message_response_dto)
    def patch(self) -> Response:
        """Transitions a task to another status with token auth"""
        request_body = request.get_json()
        task = task_service.get(request_body['task_id'], request_body['org_id'])
        return self.ok(self._transition_task(task, request_body['task_status']))

    @staticmethod
    def _transition_task(task, task_status: str, req_user=None) -> dict:
        """Transitions a task to another status"""
        task_service.transition(
            task=task,
            status=task_status,
            req_user=req_user

        )
        return task.fat_dict()


@transition_task_route.route("/<int:task_id>")
class GetTaskTransitions(RequestValidationController):
    @handle_exceptions
    @requires_jwt
    @authorize(Operations.GET, Resources.TASK_TRANSITIONS)
    @transition_task_route.response(200, "Success", task_statuses_response)
    @transition_task_route.response(400, "Failed to get the available transitions", message_response_dto)
    def get(self, task_id, **kwargs) -> Response:
        """Returns the statuses that a task could be transitioned to, based on the state of the task."""
        req_user = kwargs['req_user']

        task = self.validate_get_transitions(req_user.org_id, task_id)

        statuses = []

        # handle case where no-one is assigned to the task
        if task.assignee is None:
            # you can move from ready to ready, cancelled and dropped are not included because they are handled
            # separately
            valid_transitions = {
                TaskStatuses.READY: [TaskStatuses.READY],
                TaskStatuses.SCHEDULED: [TaskStatuses.READY]
            }

            # search list for querying db
            search = valid_transitions.get(task.status, [])

            with session_scope() as session:
                # will return all the attributes for the ready status
                enabled_qry = session.query(TaskStatus).filter(TaskStatus.status.in_(search)).all()
                # will return all other statuses
                disabled_qry = session.query(TaskStatus).filter(~TaskStatus.status.in_(search)).all()

            # enabled options
            statuses += [ts.as_dict() for ts in enabled_qry]

            # disabled options
            statuses += [
                ts.as_dict(disabled=True, tooltip="No one is assigned to this task.") for ts in disabled_qry
            ]

        else:
            # if someone is assigned to the task, then these are the available transitions
            valid_transitions = {
                TaskStatuses.READY: [TaskStatuses.READY, TaskStatuses.IN_PROGRESS, TaskStatuses.CANCELLED],
                TaskStatuses.IN_PROGRESS: [TaskStatuses.IN_PROGRESS, TaskStatuses.COMPLETED],
                TaskStatuses.DELAYED: [TaskStatuses.DELAYED, TaskStatuses.IN_PROGRESS],
                TaskStatuses.SCHEDULED: [TaskStatuses.READY]
            }

            # search list for querying db
            search = valid_transitions.get(task.status, [])

            with session_scope() as session:
                # will return all attributes for the enabled tasks
                enabled_qry = session.query(TaskStatus).filter(TaskStatus.status.in_(search)).all()
                # will return attributes for all other tasks
                disabled_qry = session.query(TaskStatus).filter(~TaskStatus.status.in_(search)).all()

            # enabled options
            statuses += [ts.as_dict() for ts in enabled_qry]

            # disabled options
            statuses += [
                ts.as_dict(disabled=True) for ts in disabled_qry
            ]

        return self.ok({'statuses': statuses})
