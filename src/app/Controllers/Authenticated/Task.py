import datetime

from flask import request, Response
from flask_restplus import Namespace

from app import logger, session_scope
from app.Exceptions import ValidationError
from app.Controllers.Base import RequestValidationController
from app.Decorators import requires_jwt, handle_exceptions, authorize, requires_token_auth
from app.Models import DelayedTask, TaskStatus, Notification
from app.Models.Enums import TaskStatuses, Operations, Resources
from app.Models.Request import assign_task_dto, delay_task_dto, get_delayed_task_dto, transition_task_dto, \
    get_available_transitions_dto
from app.Models.Response import task_response_dto, message_response_dto, delayed_task_response_dto, \
    get_task_statuses_response_dto
from app.Services import UserService, TaskService

task_route = Namespace(
    path="/task",
    name="Tasks",
    description="Manage tasks"
)

user_service = UserService()
task_service = TaskService()


@task_route.route("/<int:task_id>")
class Task(RequestValidationController):

    @handle_exceptions
    @requires_jwt
    @authorize(Operations.GET, Resources.TASK)
    @task_route.response(200, "Success", task_response_dto)
    @task_route.response(400, "Failed to get the task", message_response_dto)
    def get(self, task_id: int, **kwargs) -> Response:
        """Get a single task"""
        req_user = kwargs['req_user']

        task = task_service.get(task_id, req_user.org_id)

        req_user.log(
            operation=Operations.GET,
            resource=Resources.TASK,
            resource_id=task.id
        )
        return self.ok(task.fat_dict())


@task_route.route("/assign")
class AssignTask(RequestValidationController):

    @handle_exceptions
    @requires_jwt
    @authorize(Operations.ASSIGN, Resources.TASK)
    @task_route.expect(assign_task_dto)
    @task_route.response(200, "Success", task_response_dto)
    @task_route.response(400, "Failed to assign the task", message_response_dto)
    def post(self, **kwargs) -> Response:
        """Assigns a user to task """
        task, assignee_id = self.validate_assign_task(request.get_json(), **kwargs)
        task_service.assign(
            task=task,
            assignee=assignee_id,
            req_user=kwargs['req_user']
        )
        return self.ok(task.fat_dict())


@task_route.route("/delay")
class DelayTask(RequestValidationController):

    @handle_exceptions
    @requires_jwt
    @authorize(Operations.DELAY, Resources.TASK)
    @task_route.expect(delay_task_dto)
    @task_route.response(200, "Success", task_response_dto)
    @task_route.response(400, "Failed to delay the task", message_response_dto)
    def post(self, **kwargs) -> Response:
        """Delays a task """
        req_user = kwargs['req_user']

        task, delay_for, reason = self.validate_delay_task_request(request.get_json(), **kwargs)

        with session_scope() as session:
            # transition a task to delayed
            task_service.transition(
                task=task,
                status=TaskStatuses.DELAYED,
                req_user=req_user
            )
            # check to see if the task has been delayed previously
            delay = session.query(DelayedTask).filter_by(task_id=task.id).first()

            # if the task has been delayed before, update it, otherwise create it
            if delay is not None:
                delay.delay_for = delay_for
                delay.delayed_at = datetime.datetime.utcnow()
                delay.snoozed = None
                if reason is not None:
                    delay.reason = reason
            else:
                delayed_task = DelayedTask(
                    task_id=task.id,
                    delay_for=delay_for,
                    delayed_at=datetime.datetime.utcnow(),
                    delayed_by=req_user.id,
                    reason=reason
                )
                session.add(delayed_task)

        if req_user.id == task.assignee:
            Notification(
                msg=f"{task.label()} has been delayed.",
                user_ids=task.created_by
            ).push()
        elif req_user.id == task.created_by:
            Notification(
                msg=f"{task.label()} has been delayed.",
                user_ids=task.assignee
            ).push()

        req_user.log(
            operation=Operations.DELAY,
            resource=Resources.TASK,
            resource_id=task.id
        )
        logger.info(f"User {req_user.id} delayed task {task.id} for {delay_for}s.")
        return self.ok(task.fat_dict())

    @handle_exceptions
    @requires_jwt
    @authorize(Operations.GET, Resources.TASK)
    @task_route.expect(get_delayed_task_dto)
    @task_route.response(200, "Success", delayed_task_response_dto)
    @task_route.response(400, "Failed to delay the task", message_response_dto)
    def get(self, **kwargs) -> Response:
        """Returns the delayed info for a task """
        req_user = kwargs['req_user']
        request_body = request.get_json()
        task_id = request_body.get('task_id')

        task = task_service.get(task_id, req_user.org_id)

        req_user.log(
            operation=Operations.GET,
            resource=Resources.TASK,
            resource_id=task.id
        )

        return self.ok(task.delayed_info())


@task_route.route("/priority")
class TaskPriority(RequestValidationController):

    @handle_exceptions
    @requires_token_auth
    @task_route.response(200, "Success", message_response_dto)
    @task_route.response(400, "Failed change the priority", message_response_dto)
    def put(self) -> Response:
        """Change a tasks priority"""
        request_body = request.get_json()
        params = {
            "org_id": request_body.get('org_id'),
            "task_id": request_body.get('task_id'),
            "priority": request_body.get('priority'),
        }
        for k, v in params.items():
            if v is None:
                raise ValidationError(f"Missing {k} from request")

        task = task_service.get(params['task_id'], params['org_id'])
        task_service.change_priority(
            task=task,
            priority=params['priority']
        )
        return self.ok(f"Priority changed for task {params['task_id']}")


@task_route.route("/transition")
class TransitionTask(RequestValidationController):

    @handle_exceptions
    @requires_jwt
    @authorize(Operations.TRANSITION, Resources.TASK)
    @task_route.expect(transition_task_dto)
    @task_route.response(200, "Success", task_response_dto)
    @task_route.response(400, "Failed to transition the task", message_response_dto)
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
    @task_route.expect(get_available_transitions_dto)
    @task_route.response(200, "Success", get_task_statuses_response_dto)
    @task_route.response(400, "Failed to get the available transitions", message_response_dto)
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


@task_route.route("/cancel/<int:task_id>")
class CancelTask(RequestValidationController):

    @handle_exceptions
    @requires_jwt
    @authorize(Operations.CANCEL, Resources.TASK)
    @task_route.response(200, "Success", task_response_dto)
    @task_route.response(400, "Failed to cancel the task", message_response_dto)
    def post(self, task_id: int, **kwargs) -> Response:
        """Cancels a task"""
        req_user = kwargs['req_user']

        task_to_cancel = self.validate_cancel_task(task_id, **kwargs)

        task_service.transition(
            task=task_to_cancel,
            status=TaskStatuses.CANCELLED,
            req_user=req_user
        )
        req_user.log(
            operation=Operations.CANCEL,
            resource=Resources.TASK,
            resource_id=task_id
        )
        if task_to_cancel.assignee is not None:
            Notification(
                msg=f"{task_to_cancel.label()} cancelled.",
                user_ids=task_to_cancel.assignee
            ).push()
        logger.info(f"User {req_user.id} cancelled task {task_to_cancel.id}")
        return self.ok(task_to_cancel.fat_dict())


@task_route.route("/drop/<int:task_id>")
class DropTask(RequestValidationController):

    @handle_exceptions
    @requires_jwt
    @authorize(Operations.DROP, Resources.TASK)
    @task_route.response(200, "Success", task_response_dto)
    @task_route.response(400, "Failed to drop the task", message_response_dto)
    def post(self, task_id: int, **kwargs) -> Response:
        """Drops a task"""
        task_to_drop = self.validate_drop_task(task_id, **kwargs)
        task_service.drop(task_to_drop, kwargs['req_user'])
        return self.ok(task_to_drop.fat_dict())
