from flask import Response
from flask_restplus import Namespace

from app.Controllers.Base import RequestValidationController
from app.Decorators import requires_jwt, handle_exceptions, authorize
from app.Models.Enums import Operations, Resources
from app.Models.Response import task_response, message_response_dto
from app.Services import TaskService

task_route = Namespace(
    path="/task",
    name="Tasks",
    description="Manage tasks"
)

task_service = TaskService()


@task_route.route("/<int:task_id>")
class Task(RequestValidationController):

    @handle_exceptions
    @requires_jwt
    @authorize(Operations.GET, Resources.TASK)
    @task_route.response(200, "Success", task_response)
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
