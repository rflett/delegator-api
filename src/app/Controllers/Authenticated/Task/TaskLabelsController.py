from flask import request
from flask_restx import Namespace, fields

from app.Controllers.Base import RequestValidationController
from app.Decorators import requires_jwt, authorize
from app.Extensions.Database import session_scope
from app.Extensions.Errors import ResourceNotFoundError
from app.Models.Dao import TaskLabel
from app.Models.Enums import Operations, Resources

api = Namespace(path="/task-labels", name="Task Labels", description="Manage Task Labels")


@api.route("/")
class TaskLabels(RequestValidationController):

    task_label_dto = api.model(
        "Get Task Label Dto", {"id": fields.Integer(), "label": fields.String(), "colour": fields.String()}
    )
    task_labels_response = api.model("Get Labels Response", {"labels": fields.List(fields.Nested(task_label_dto))})

    @requires_jwt
    @authorize(Operations.GET, Resources.TASK_LABELS)
    @api.marshal_with(task_labels_response, code=200)
    def get(self, **kwargs):
        """Returns all task labels """
        req_user = kwargs["req_user"]

        with session_scope() as session:
            task_labels_qry = session.query(TaskLabel).filter_by(org_id=req_user.org_id).order_by(TaskLabel.id).all()

        req_user.log(Operations.GET, Resources.TASK_LABELS)
        return {"labels": [tl.as_dict() for tl in task_labels_qry]}, 200

    create_label_dto = api.model(
        "Create Label Dto", {"label": fields.String(required=True), "colour": fields.String(required=True)}
    )

    @requires_jwt
    @authorize(Operations.CREATE, Resources.TASK_LABEL)
    @api.expect(create_label_dto, validate=True)
    @api.response(204, "Success")
    def post(self, **kwargs):
        """Creates a task label"""
        req_user = kwargs["req_user"]
        request_body = request.get_json()

        with session_scope() as session:
            new_label = TaskLabel(req_user.org_id, request_body["label"], request_body["colour"])
            session.add(new_label)

        req_user.log(Operations.CREATE, Resources.TASK_LABEL, new_label.id)
        return "", 204

    @requires_jwt
    @authorize(Operations.UPDATE, Resources.TASK_LABEL)
    @api.expect(task_label_dto, validate=True)
    @api.response(204, "Success")
    def put(self, **kwargs):
        """Updates a task label"""
        req_user = kwargs["req_user"]
        request_body = request.get_json()

        with session_scope() as session:
            label = session.query(TaskLabel).filter_by(id=request_body["id"], org_id=req_user.org_id).first()
            if label is None:
                raise ResourceNotFoundError(f"Label {request_body['id']} doesn't exist")
            else:
                label.colour = request_body["colour"]
                label.label = request_body["label"]

        req_user.log(Operations.UPDATE, Resources.TASK_LABEL, label.id)
        return "", 204


@api.route("/<int:label_id>")
class DeleteTaskLabel(RequestValidationController):
    @requires_jwt
    @authorize(Operations.DELETE, Resources.TASK_LABEL)
    @api.param("label_id", "The id of the label you want to delete")
    @api.response(204, "Deleted the task label")
    def delete(self, label_id: int, **kwargs):
        """Deletes a task label"""
        req_user = kwargs["req_user"]

        with session_scope() as session:
            label = session.query(TaskLabel).filter_by(id=label_id, org_id=req_user.org_id).first()
            if label is None:
                raise ResourceNotFoundError(f"Label {label_id} doesn't exist")
            session.delete(label)

        req_user.log(Operations.DELETE, Resources.TASK_LABEL, label_id)
        return "", 204
