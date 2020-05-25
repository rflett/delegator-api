import datetime

from flask import request
from flask_restx import Namespace, fields
from sqlalchemy import func

from app.Controllers.Base import RequestValidationController
from app.Decorators import requires_jwt, authorize
from app.Extensions.Database import session_scope
from app.Extensions.Errors import ValidationError, ResourceNotFoundError
from app.Models import Event
from app.Models.Dao import TaskTemplate
from app.Models.Enums import Events, Operations, Resources

api = Namespace(path="/task-templates", name="Task Templates", description="Manage Task Templates")


class NullableDateTime(fields.DateTime):
    __schema_type__ = ["string", "null"]
    __schema_example__ = "None|2019-09-17T19:08:00+10:00"


@api.route("/")
class TaskTypes(RequestValidationController):

    escalation_dto = api.model(
        "Get Templates Escalation dto",
        {
            "id": fields.Integer(),
            "delay": fields.Integer(),
            "from_priority": fields.Integer(),
            "to_priority": fields.Integer(),
        },
    )
    task_template_response = api.model(
        "Task Template Response",
        {
            "id": fields.Integer(),
            "org_id": fields.Integer(),
            "disabled": NullableDateTime,
            "title": fields.String(),
            "default_time_estimate": fields.Integer(),
            "default_description": fields.String(),
            "default_priority": fields.Integer(),
            "tooltip": fields.String(),
            "escalations": fields.List(fields.Nested(escalation_dto)),
        },
    )
    get_response_dto = api.model(
        "Get Task Templates Response", {"templates": fields.List(fields.Nested(task_template_response))}
    )

    @requires_jwt
    @authorize(Operations.GET, Resources.TASK_TEMPLATES)
    @api.marshal_with(get_response_dto, code=200)
    def get(self, **kwargs):
        """Returns all task templates"""
        req_user = kwargs["req_user"]

        with session_scope() as session:
            task_template_qry = session.query(TaskTemplate).filter_by(org_id=req_user.org_id, disabled=None).all()

            task_templates = []
            for tt in task_template_qry:
                tt_dict = tt.as_dict()
                tt_dict["escalations"] = [e.as_dict() for e in tt.escalations]
                task_templates.append(tt_dict)

        req_user.log(Operations.GET, Resources.TASK_TEMPLATES)
        return {"templates": task_templates}, 200

    create_request = api.model(
        "Create Task Template Request",
        {
            "title": fields.String(required=True),
            "default_time_estimate": fields.Integer(min=-1, required=True),
            "default_priority": fields.Integer(enum=[-1, 0, 1, 2], required=True),
            "default_description": fields.String(),
        },
    )

    @requires_jwt
    @authorize(Operations.CREATE, Resources.TASK_TEMPLATE)
    @api.expect(create_request, validate=True)
    @api.marshal_with(task_template_response, code=201)
    def post(self, **kwargs):
        """Creates a task template"""
        req_user = kwargs["req_user"]
        request_body = request.get_json()

        # check if the template already exists
        with session_scope() as session:
            task_template = (
                session.query(TaskTemplate)
                .filter(
                    func.lower(TaskTemplate.title) == func.lower(request_body["title"]),
                    TaskTemplate.org_id == req_user.org_id,
                )
                .first()
            )

        if task_template is None:
            # it didn't exist so just create it
            with session_scope() as session:
                new_template = TaskTemplate(
                    title=request_body["title"],
                    org_id=req_user.org_id,
                    disabled=None,
                    default_time_estimate=request_body["default_time_estimate"],
                    default_priority=request_body["default_priority"],
                    default_description=request_body.get("default_description"),
                )
                session.add(new_template)
            tt_dict = new_template.as_dict()
            tt_dict["escalations"] = [e.as_dict() for e in new_template.escalations]
            req_user.log(Operations.CREATE, Resources.TASK_TEMPLATE, new_template.id)
        else:
            # it existed so check if it needs to be enabled
            if task_template.disabled is None:
                raise ValidationError(f"Template with title {request_body['title']} already exists.")
            with session_scope():
                task_template.disabled = None
            tt_dict = task_template.as_dict()
            tt_dict["escalations"] = [e.as_dict() for e in task_template.escalations]
            req_user.log(Operations.ENABLE, Resources.TASK_TEMPLATE, task_template.id)

        return tt_dict, 201

    update_request = api.model(
        "Update Task Template Request",
        {
            "id": fields.Integer(required=True),
            "title": fields.String(required=True),
            "default_time_estimate": fields.Integer(min=-1, required=True),
            "default_priority": fields.Integer(enum=[-1, 0, 1, 2], required=True),
            "default_description": fields.String(),
        },
    )

    @requires_jwt
    @authorize(Operations.UPDATE, Resources.TASK_TEMPLATE)
    @api.expect(update_request, validate=True)
    @api.response(204, "Success")
    def put(self, **kwargs):
        """Updates a task template"""
        req_user = kwargs["req_user"]
        request_body = request.get_json()

        # check that the task template exists
        with session_scope() as session:
            task_template = (
                session.query(TaskTemplate)
                .filter_by(id=request_body["id"], org_id=req_user.org_id, disabled=None)
                .first()
            )

        if task_template is None:
            raise ResourceNotFoundError(f"Template {request_body['title']} doesn't exist.")

        # update title and defaults
        with session_scope():
            task_template.title = request_body["title"]
            task_template.default_time_estimate = request_body["default_time_estimate"]
            task_template.default_priority = request_body["default_priority"]
            task_template.default_description = request_body.get("default_description")

        return "", 204


@api.route("/<int:template_id>")
class DeleteTaskType(RequestValidationController):
    @requires_jwt
    @authorize(Operations.DISABLE, Resources.TASK_TEMPLATE)
    @api.response(204, "Success")
    def delete(self, template_id, **kwargs):
        """Disables a task template"""
        req_user = kwargs["req_user"]

        with session_scope() as session:
            task_template = (
                session.query(TaskTemplate).filter_by(id=template_id, org_id=req_user.org_id, disabled=None).first()
            )

            if task_template is None:
                raise ResourceNotFoundError(f"Task template {template_id} doesn't exist.")
            else:
                task_template.disabled = datetime.datetime.utcnow()

        Event(
            org_id=req_user.org_id,
            event=Events.user_disabled_tasktemplate,
            event_id=req_user.id,
            event_friendly=f"Deleted task template {task_template.title}.",
        ).publish()
        req_user.log(Operations.DISABLE, Resources.TASK_TEMPLATE, task_template.id)
        return "", 204
