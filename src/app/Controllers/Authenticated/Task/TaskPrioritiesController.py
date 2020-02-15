from flask import request
from flask_restx import Namespace, fields

from app.Controllers.Base import RequestValidationController
from app.Decorators import requires_jwt, authorize
from app.Extensions.Database import session_scope
from app.Models import TaskPriority
from app.Models.Enums import Operations, Resources
from app.Services import TaskService

api = Namespace(path="/tasks/priorities", name="Tasks", description="Manage tasks")

task_service = TaskService()


@api.route("/")
class TaskPriorities(RequestValidationController):

    task_priority_dto = api.model("Task Priority", {"priority": fields.Integer(min=0, max=1), "label": fields.String()})
    get_response = api.model(
        "Task Priorities Response", {"priorities": fields.List(fields.Nested(task_priority_dto))}
    )

    @requires_jwt
    @authorize(Operations.GET, Resources.TASK_PRIORITIES)
    @api.marshal_with(get_response, code=200)
    def get(self, **kwargs):
        """Returns all task priorities """
        req_user = kwargs["req_user"]

        with session_scope() as session:
            qry = session.query(TaskPriority).all()

        task_priorities = [tp.as_dict() for tp in qry]
        req_user.log(operation=Operations.GET, resource=Resources.TASK_PRIORITIES)
        return {"priorities": task_priorities}, 200

    update_dto = api.model(
        "Update Task Priority Request",
        {"task_id": fields.Integer(required=True), "priority": fields.Integer(min=0, max=2, required=True)},
    )

    @requires_jwt
    @authorize(Operations.UPDATE, Resources.TASK_PRIORITY)
    @api.expect(update_dto, validate=True)
    @api.response(204, "Success")
    def put(self, **kwargs):
        """Change a tasks priority"""
        req_user = kwargs["req_user"]
        request_body = request.get_json()

        task = task_service.get(request_body["task_id"], req_user.org_id)
        task_service.change_priority(task, request_body["priority"])

        req_user.log(Operations.UPDATE, Resources.TASK_PRIORITY, task.id)
        return "", 204
