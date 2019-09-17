from flask import Response, request
from flask_restplus import Namespace

from app import session_scope
from app.Controllers.Base import RequestValidationController
from app.Decorators import requires_jwt, handle_exceptions, authorize, requires_token_auth
from app.Exceptions import ValidationError
from app.Models import TaskPriority
from app.Models.Enums import Operations, Resources
from app.Models.Request import update_task_priority_request
from app.Models.Response import task_priorities_response, message_response_dto
from app.Services import TaskService

task_priorities_route = Namespace(
    path="/tasks/priorities",
    name="Tasks",
    description="Manage tasks"
)

task_service = TaskService()


@task_priorities_route.route('/')
class TaskPriorities(RequestValidationController):

    @handle_exceptions
    @requires_jwt
    @authorize(Operations.GET, Resources.TASK_PRIORITIES)
    @task_priorities_route.response(200, "Success", task_priorities_response)
    def get(self, **kwargs) -> Response:
        """Returns all task priorities """
        req_user = kwargs['req_user']

        with session_scope() as session:
            task_pr_qry = session.query(TaskPriority).all()

        task_priorities = [tp.as_dict() for tp in task_pr_qry]
        req_user.log(
            operation=Operations.GET,
            resource=Resources.TASK_PRIORITIES
        )
        return self.ok({'priorities': task_priorities})

    @handle_exceptions
    @requires_token_auth
    @task_priorities_route.expect(update_task_priority_request)
    @task_priorities_route.response(200, "Success", message_response_dto)
    @task_priorities_route.response(400, "Failed change the priority", message_response_dto)
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
