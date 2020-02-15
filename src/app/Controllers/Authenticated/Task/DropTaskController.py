from flask_restx import Namespace

from app.Controllers.Base import RequestValidationController
from app.Decorators import requires_jwt, authorize
from app.Models.Enums import Operations, Resources
from app.Services import TaskService

api = Namespace(path="/task/drop", name="Task", description="Manage a task")

task_service = TaskService()


@api.route("/<int:task_id>")
class DropTask(RequestValidationController):
    @requires_jwt
    @authorize(Operations.DROP, Resources.TASK)
    @api.response(204, "Success")
    def post(self, task_id: int, **kwargs):
        """Drops a task"""
        task_to_drop = self.validate_drop_task(task_id, **kwargs)
        task_service.drop(task_to_drop, kwargs["req_user"])
        return "", 204
