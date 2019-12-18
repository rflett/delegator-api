from flask import request, Response
from flask_restplus import Namespace

from app import session_scope
from app.Controllers.Base import RequestValidationController
from app.Decorators import requires_jwt, handle_exceptions, authorize
from app.Models import TaskStatus, Task
from app.Models.Enums import TaskStatuses, Operations, Resources
from app.Models.RBAC import ServiceAccount
from app.Models.Request import transition_task_request
from app.Models.Response import task_response, message_response_dto, transition_tasks_response
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
    @transition_task_route.response(200, "Transitioned the task to another status", task_response)
    @transition_task_route.response(400, "Bad request", message_response_dto)
    @transition_task_route.response(403, "Insufficient privileges", message_response_dto)
    @transition_task_route.response(404, "Task not found", message_response_dto)
    def put(self, **kwargs) -> Response:
        """Transitions a task to another status"""
        req_user = kwargs['req_user']
        request_body = request.get_json()

        if isinstance(req_user, ServiceAccount):
            task = task_service.get(request_body['task_id'], request_body['org_id'])
            result = self._transition_task(task, request_body['task_status'])
        else:
            task, task_status = self.validate_transition_task(request.get_json(), **kwargs)
            result = self._transition_task(task, task_status, kwargs['req_user'])

        return self.ok(result)

    @staticmethod
    def _transition_task(task, task_status: str, req_user=None) -> dict:
        """Transitions a task to another status"""
        task_service.transition(
            task=task,
            status=task_status,
            req_user=req_user

        )
        return task.fat_dict()

    @handle_exceptions
    @requires_jwt
    @authorize(Operations.GET, Resources.TASK_TRANSITIONS)
    @transition_task_route.response(200, "Success", transition_tasks_response)
    @transition_task_route.response(400, "Bad request", message_response_dto)
    @transition_task_route.response(403, "Insufficient privileges", message_response_dto)
    @transition_task_route.response(404, "Task not found", message_response_dto)
    def get(self, **kwargs) -> Response:
        """Returns all tasks and the statuses they can be transitioned to"""
        req_user = kwargs['req_user']

        with session_scope() as session:
            tasks = session.query(Task).filter_by(org_id=req_user.org_id).all()

        # handle case where no-one is assigned to the task
        all_task_transitions = []
        for task in tasks:
            this_task_transitions = {
                "task_id": task.id,
                "valid_transitions": []
            }

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

                # enabled options
                this_task_transitions["valid_transitions"] += [ts.status for ts in enabled_qry]

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

                # enabled options
                this_task_transitions["valid_transitions"] += [ts.status for ts in enabled_qry]

            all_task_transitions.append(this_task_transitions)

        return self.ok(all_task_transitions)
