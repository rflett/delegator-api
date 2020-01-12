from flask import Response
from flask_restplus import Namespace

from app.Controllers.Base import RequestValidationController
from app.Decorators import requires_jwt, handle_exceptions, authorize
from app.Models.Enums import Operations, Resources
from app.Models.Response import task_response, message_response_dto
from app.Services import TaskService

drop_task_route = Namespace(path="/task/drop", name="Task", description="Manage a task")

task_service = TaskService()


@drop_task_route.route("/<int:task_id>")
class DropTask(RequestValidationController):
    @handle_exceptions
    @requires_jwt
    @authorize(Operations.DROP, Resources.TASK)
    @drop_task_route.response(200, "Dropped the task", task_response)
    @drop_task_route.response(400, "Bad request", message_response_dto)
    @drop_task_route.response(403, "Insufficient privileges", message_response_dto)
    @drop_task_route.response(404, "Task not found", message_response_dto)
    def post(self, task_id: int, **kwargs) -> Response:
        """Drops a task"""
        task_to_drop = self.validate_drop_task(task_id, **kwargs)
        task_service.drop(task_to_drop, kwargs["req_user"])
        return self.ok(task_to_drop.fat_dict())
