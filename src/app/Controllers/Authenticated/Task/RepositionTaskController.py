from flask import current_app, request
from flask_restx import Namespace, fields

from app.Controllers.Base import RequestValidationController
from app.Decorators import requires_jwt, authorize
from app.Extensions.Database import session_scope
from app.Models import Event
from app.Models.Enums import Operations, Resources, Events
from app.Services import TaskService

api = Namespace(path="/task/reposition", name="Task", description="Manage a task")

task_service = TaskService()


@api.route("/")
class RepositionTask(RequestValidationController):

    reposition_task_dto = api.model(
        "Reposition Task Request",
        {"task_id": fields.Integer(required=True), "display_order": fields.Integer(required=True, min=0)},
    )

    @requires_jwt
    @authorize(Operations.UPDATE, Resources.TASK_POSITION)
    @api.expect(reposition_task_dto, validate=True)
    @api.response(204, "Success")
    def post(self, **kwargs):
        """Repositions a task"""
        req_user = kwargs["req_user"]
        request_body = request.get_json()

        task_to_repo = self.check_task_id(request_body["task_id"], kwargs["req_user"].org_id)

        if task_to_repo.display_order != request_body["display_order"]:
            task_service.reindex_display_orders(task_to_repo.org_id, request_body["display_order"])

        with session_scope():
            task_to_repo.display_order = request_body["display_order"]

        req_user.log(Operations.UPDATE, Resources.TASK_POSITION, resource_id=task_to_repo.id)
        current_app.logger.info(f"User {req_user.id} repositioned task {task_to_repo.id}")
        Event(
            org_id=req_user.org_id,
            event=Events.task_repositioned,
            event_id=task_to_repo.id,
            event_friendly="Task repositioned in UI.",
            store_in_db=False,
        ).publish()

        return "", 204
