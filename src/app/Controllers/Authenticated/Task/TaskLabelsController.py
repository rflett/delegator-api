from flask import Response, request
from flask_restplus import Namespace

from app import session_scope, logger
from app.Controllers.Base import RequestValidationController
from app.Decorators import requires_jwt, handle_exceptions, authorize
from app.Models import TaskLabel
from app.Models.Enums import Operations, Resources
from app.Models.Response import task_labels_response, message_response_dto
from app.Models.Request import new_task_label_dto, task_label_dto

task_labels_route = Namespace(path="/task-labels", name="Task Labels", description="Manage Task Labels")


@task_labels_route.route("/")
class TaskLabels(RequestValidationController):
    @handle_exceptions
    @requires_jwt
    @authorize(Operations.GET, Resources.TASK_LABELS)
    @task_labels_route.response(200, "Success", task_labels_response)
    @task_labels_route.response(403, "Insufficient privileges", message_response_dto)
    def get(self, **kwargs) -> Response:
        """Returns all task labels """
        req_user = kwargs["req_user"]

        with session_scope() as session:
            task_labels_qry = session.query(TaskLabel).filter_by(org_id=req_user.org_id).all()

        req_user.log(Operations.GET, Resources.TASK_LABELS)
        return self.ok({"labels": [tl.as_dict() for tl in task_labels_qry]})

    @handle_exceptions
    @requires_jwt
    @authorize(Operations.CREATE, Resources.TASK_LABEL)
    @task_labels_route.expect(new_task_label_dto)
    @task_labels_route.response(200, "Created task label", task_label_dto)
    @task_labels_route.response(400, "Bad request", message_response_dto)
    @task_labels_route.response(403, "Insufficient privileges", message_response_dto)
    def post(self, **kwargs) -> Response:
        """Creates a task label"""
        req_user = kwargs["req_user"]
        request_body = request.get_json()

        label, colour = self.validate_create_task_label_request(request_body)

        with session_scope() as session:
            new_label = TaskLabel(req_user.org_id, label, colour)
            session.add(new_label)

        req_user.log(Operations.CREATE, Resources.TASK_LABEL, new_label.id)
        return self.created(new_label.as_dict())

    @handle_exceptions
    @requires_jwt
    @authorize(Operations.UPDATE, Resources.TASK_LABEL)
    @task_labels_route.expect(task_label_dto)
    @task_labels_route.response(200, "Updated the task label", task_label_dto)
    @task_labels_route.response(400, "Bad request", message_response_dto)
    @task_labels_route.response(403, "Insufficient privileges", message_response_dto)
    @task_labels_route.response(404, "Task label not found", message_response_dto)
    def put(self, **kwargs) -> Response:
        """Updates a task label"""
        req_user = kwargs["req_user"]
        request_body = request.get_json()

        label = self.validate_update_task_labels_request(request_body, req_user.org_id)

        logger.info(label.id)

        with session_scope():
            label.colour = request_body.get("colour")
            label.label = request_body.get("label")

        req_user.log(Operations.UPDATE, Resources.TASK_LABEL, label.id)
        return self.ok(label.as_dict())


@task_labels_route.route("/<int:label_id>")
class DeleteTaskLabel(RequestValidationController):
    @handle_exceptions
    @requires_jwt
    @authorize(Operations.DELETE, Resources.TASK_LABEL)
    @task_labels_route.param("label_id", "The id of the label you want to delete")
    @task_labels_route.response(204, "Deleted the task label")
    @task_labels_route.response(400, "Bad request", message_response_dto)
    @task_labels_route.response(403, "Insufficient privileges", message_response_dto)
    @task_labels_route.response(404, "Task label not found", message_response_dto)
    def delete(self, label_id: int, **kwargs) -> Response:
        """Deletes a task label"""
        req_user = kwargs["req_user"]

        label = self.validate_delete_task_labels_request(label_id, req_user.org_id)

        with session_scope() as session:
            session.delete(label)

        req_user.log(Operations.DELETE, Resources.TASK_LABEL, label_id)
        return self.no_content()
