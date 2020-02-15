from flask import request
from flask_restx import Namespace, fields

from app.Controllers.Base import RequestValidationController
from app.Decorators import requires_jwt, authorize
from app.Models.Enums import Operations, Resources
from app.Services import TaskService

task_service = TaskService()

api = Namespace(path="/task/assign", name="Task", description="Manage a task")
request_dto = api.model(
    "Assign Task Request", {"task_id": fields.Integer(required=True), "assignee": fields.Integer(required=True),}
)


@api.route("/")
class AssignTask(RequestValidationController):
    @requires_jwt
    @authorize(Operations.ASSIGN, Resources.TASK)
    @api.expect(request_dto, validate=True)
    @api.response(204, "Success")
    def post(self, **kwargs):
        """Assigns a user to task """
        request_body = request.get_json()

        # validate
        task = self.check_task_id(request_body["task_id"], kwargs["req_user"].org_id)
        assignee_id = self.check_task_assignee(request_body["assignee"], **kwargs)

        # assign
        task_service.assign(task=task, assignee=assignee_id, req_user=kwargs["req_user"])

        return "", 204
