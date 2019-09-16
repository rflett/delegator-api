from flask import request, Response
from flask_restplus import Namespace

from app import session_scope
from app.Controllers.Base import RequestValidationController
from app.Decorators import requires_jwt, handle_exceptions, authorize
from app.Models import TaskStatus
from app.Models.Enums import TaskStatuses, Operations, Resources
from app.Models.Request import transition_task_dto, get_available_transitions_dto
from app.Models.Response import task_response_dto, message_response_dto, get_task_statuses_response_dto
from app.Services import TaskService

transition_task_route = Namespace(
    path="/task/transition",
    name="Tasks",
    description="Manage tasks"
)

task_service = TaskService()


@transition_task_route.route("/")
class TransitionTask(RequestValidationController):

    @handle_exceptions
    @requires_jwt
    @authorize(Operations.TRANSITION, Resources.TASK)
    @transition_task_route.expect(transition_task_dto)
    @transition_task_route.response(200, "Success", task_response_dto)
    @transition_task_route.response(400, "Failed to transition the task", message_response_dto)
    def post(self, **kwargs) -> Response:
        """Transitions a task to another status"""
        task, task_status = self.validate_transition_task(request.get_json(), **kwargs)
        task_service.transition(
            task=task,
            status=task_status,
            req_user=kwargs['req_user']

        )
        return self.ok(task.fat_dict())

    @handle_exceptions
    @requires_jwt
    @authorize(Operations.GET, Resources.TASK_TRANSITIONS)
    @transition_task_route.expect(get_available_transitions_dto)
    @transition_task_route.response(200, "Success", get_task_statuses_response_dto)
    @transition_task_route.response(400, "Failed to get the available transitions", message_response_dto)
    def get(self, **kwargs) -> Response:
        """Returns the statuses that a task could be transitioned to, based on the state of the task."""
        req_user = kwargs['req_user']
        request_body = request.get_json()
        task_id = request_body.get('task_id')

        task = self.validate_get_transitions(req_user.org_id, task_id)

        transitions = []

        # handle case where no-one is assigned to the task
        if task.assignee is None:
            # you can move from ready to ready, cancelled and dropped are not included because they are handled
            # separately
            valid_transitions = {
                TaskStatuses.READY: [TaskStatuses.READY]
            }

            # search list for querying db
            search = valid_transitions.get(task.status, [])

            with session_scope() as session:
                # will return all the attributes for the ready status
                enabled_qry = session.query(TaskStatus).filter(TaskStatus.status.in_(search)).all()
                # will return all other statuses
                disabled_qry = session.query(TaskStatus).filter(~TaskStatus.status.in_(search)).all()

            # enabled options
            transitions += [ts.as_dict() for ts in enabled_qry]

            # disabled options
            transitions += [ts.as_dict(disabled=True, tooltip="No one is assigned to this task.") for ts in disabled_qry]

        else:
            # if someone is assigned to the task, then these are the available transitions
            valid_transitions = {
                TaskStatuses.READY: [TaskStatuses.READY, TaskStatuses.IN_PROGRESS, TaskStatuses.CANCELLED],
                TaskStatuses.IN_PROGRESS: [TaskStatuses.IN_PROGRESS, TaskStatuses.COMPLETED],
                TaskStatuses.DELAYED: [TaskStatuses.DELAYED, TaskStatuses.IN_PROGRESS]
            }

            # search list for querying db
            search = valid_transitions.get(task.status, [])

            with session_scope() as session:
                # will return all attributes for the enabled tasks
                enabled_qry = session.query(TaskStatus).filter(TaskStatus.status.in_(search)).all()
                # will return attributes for all other tasks
                disabled_qry = session.query(TaskStatus).filter(~TaskStatus.status.in_(search)).all()

            # enabled options
            transitions += [ts.as_dict() for ts in enabled_qry if ts.status not in ["DELAYED", "CANCELLED"]]

            # disabled options
            transitions += [ts.as_dict(disabled=True) for ts in disabled_qry if ts.status not in ["DELAYED", "CANCELLED"]]

        return self.ok(transitions)
