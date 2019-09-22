from flask import request, Response
from flask_restplus import Namespace

from app.Controllers.Base import RequestValidationController
from app.Decorators import requires_jwt, handle_exceptions, authorize
from app.Models.Enums import Operations, Resources
from app.Models.Request import assign_task_request
from app.Models.Response import task_response, message_response_dto
from app.Services import TaskService

assign_task_route = Namespace(
    path="/task/assign",
    name="Tasks",
    description="Manage tasks"
)

task_service = TaskService()


@assign_task_route.route("/")
class AssignTask(RequestValidationController):

    @handle_exceptions
    @requires_jwt
    @authorize(Operations.ASSIGN, Resources.TASK)
    @assign_task_route.expect(assign_task_request)
    @assign_task_route.response(200, "Success", task_response)
    @assign_task_route.response(400, "Failed to assign the task", message_response_dto)
    def post(self, **kwargs) -> Response:
        """Assigns a user to task """
        task, assignee_id = self.validate_assign_task(request.get_json(), **kwargs)
        task_service.assign(
            task=task,
            assignee=assignee_id,
            req_user=kwargs['req_user']
        )
        return self.ok(task.fat_dict())
