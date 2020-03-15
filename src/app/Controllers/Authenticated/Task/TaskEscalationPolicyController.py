from flask import request, current_app
from flask_restx import Namespace, fields
from sqlalchemy import and_

from app.Controllers.Base import RequestValidationController
from app.Decorators import requires_jwt, authorize
from app.Extensions.Database import session_scope
from app.Extensions.Errors import ResourceNotFoundError
from app.Models import Activity
from app.Models.Dao import TaskTemplate, TaskTemplateEscalation
from app.Models.Enums import Events, Operations, Resources

api = Namespace(path="/task-templates", name="Task Templates", description="Manage Task Templates")


class NullableDateTime(fields.DateTime):
    __schema_type__ = ["string", "null"]
    __schema_example__ = "None|2019-09-17T19:08:00+10:00"


@api.route("/<int:template_id>/escalation")
class EscalationPolicies(RequestValidationController):

    create_request = api.model(
        "Create Template Escalation Policy Request",
        {
            "delay": fields.Integer(required=True, min=0),
            "from_priority": fields.Integer(required=True, min=0, max=2),
            "to_priority": fields.Integer(required=True, min=1, max=2),
        },
    )

    @requires_jwt
    @authorize(Operations.CREATE, Resources.TASK_TEMPLATE_ESCALATION)
    @api.expect(create_request, validate=True)
    @api.response(204, "Success")
    def post(self, template_id, **kwargs):
        """Create a escalation policy"""
        req_user = kwargs["req_user"]
        request_body = request.get_json()

        with session_scope() as session:
            task_template = (
                session.query(TaskTemplate).filter_by(id=template_id, org_id=req_user.org_id, disabled=None).first()
            )
            if task_template is None:
                raise ResourceNotFoundError(f"Template {template_id} not found.")

        self.check_task_priority(request_body["from_priority"])
        self.check_task_priority(request_body["to_priority"])

        with session_scope() as session:
            new_policy = TaskTemplateEscalation(
                org_id=req_user.org_id,
                template_id=template_id,
                delay=request_body["delay"],
                from_priority=request_body["from_priority"],
                to_priority=request_body["to_priority"],
            )
            session.add(new_policy)

        Activity(
            org_id=req_user.org_id,
            event=Events.user_created_tasktemplate_escalation,
            event_id=req_user.id,
            event_friendly=f"Created escalation for {task_template.title}.",
        ).publish()
        req_user.log(Operations.CREATE, Resources.TASK_TEMPLATE_ESCALATION, task_template.id)
        current_app.logger.info(f"created task type escalation {new_policy.as_dict()}")

        return "", 204

    update_request = api.model(
        "Update Template Escalation Policy Request",
        {
            "id": fields.Integer(required=True),
            "delay": fields.Integer(required=True, min=0),
            "from_priority": fields.Integer(required=True, min=0, max=2),
            "to_priority": fields.Integer(required=True, min=1, max=2),
        },
    )

    @requires_jwt
    @authorize(Operations.UPDATE, Resources.TASK_TEMPLATE_ESCALATION)
    @api.expect(update_request, validate=True)
    @api.response(204, "Success")
    def put(self, template_id, **kwargs):
        """Update a escalation policy"""
        req_user = kwargs["req_user"]
        request_body = request.get_json()

        self.check_task_priority(request_body["from_priority"])
        self.check_task_priority(request_body["to_priority"])

        # check that the template and policy exist
        with session_scope() as session:
            qry = (
                session.query(TaskTemplate.title, TaskTemplateEscalation)
                .filter(
                    and_(
                        TaskTemplate.id == template_id,
                        TaskTemplateEscalation.id == request_body["id"],
                        TaskTemplateEscalation.org_id == req_user.org_id,
                    )
                )
                .join(TaskTemplateEscalation, TaskTemplateEscalation.template_id == template_id)
                .first()
            )
            if qry is None:
                raise ResourceNotFoundError("Escalation not found")

            title, escalation = qry

            escalation.delay = request_body["delay"]
            escalation.from_priority = request_body["from_priority"]
            escalation.to_priority = request_body["to_priority"]

        Activity(
            org_id=req_user.org_id,
            event=Events.user_updated_tasktemplate_escalation,
            event_id=req_user.id,
            event_friendly=f"Updated escalation for {title}.",
        ).publish()
        req_user.log(Operations.UPDATE, Resources.TASK_TEMPLATE_ESCALATION, escalation.id)
        current_app.logger.info(f"updated task type escalation {escalation.as_dict()}")

        return "", 204


@api.route("/<int:template_id>/escalation/<int:escalation_id>")
class DeleteEscalationPolicies(RequestValidationController):
    @requires_jwt
    @authorize(Operations.DELETE, Resources.TASK_TEMPLATE_ESCALATION)
    @api.response(204, "Success")
    def delete(self, template_id, escalation_id, **kwargs):
        """Delete an escalation policy"""
        req_user = kwargs["req_user"]

        with session_scope() as session:
            qry = (
                session.query(TaskTemplate.title)
                .filter(
                    and_(
                        TaskTemplate.id == template_id,
                        TaskTemplateEscalation.template_id == template_id,
                        TaskTemplateEscalation.org_id == req_user.org_id,
                        TaskTemplateEscalation.id == escalation_id,
                    )
                )
                .join(TaskTemplateEscalation, TaskTemplateEscalation.template_id == template_id)
                .first()
            )
            if qry is None:
                raise ResourceNotFoundError(f"Escalation {escalation_id} doesn't exist.")

            else:
                (
                    session.query(TaskTemplateEscalation)
                    .filter_by(id=escalation_id, template_id=template_id, org_id=req_user.org_id)
                    .delete(synchronize_session=False)
                )
                current_app.logger.info(f"deleted escalation id={escalation_id}, template_id={template_id}")

        Activity(
            org_id=req_user.org_id,
            event=Events.user_deleted_tasktemplate_escalation,
            event_id=req_user.id,
            event_friendly=f"Deleted escalation rule for {qry[0]}.",
        ).publish()
        req_user.log(Operations.DELETE, Resources.TASK_TEMPLATE_ESCALATION, escalation_id)
        return "", 204
