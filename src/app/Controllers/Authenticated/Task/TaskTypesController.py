import datetime

from flask import request, current_app
from flask_restx import Namespace, fields
from sqlalchemy import and_, func, exists

from app.Controllers.Base import RequestValidationController
from app.Decorators import requires_jwt, authorize
from app.Extensions.Database import session_scope
from app.Extensions.Errors import ValidationError, ResourceNotFoundError
from app.Models import Activity
from app.Models.Dao import TaskType, TaskTypeEscalation
from app.Models.Enums import Events, Operations, Resources

api = Namespace(path="/task-types", name="Task Types", description="Manage Task Types")


class NullableDateTime(fields.DateTime):
    __schema_type__ = ["datetime", "null"]
    __schema_example__ = "None|2019-09-17T19:08:00+10:00"


@api.route("/")
class TaskTypes(RequestValidationController):
    escalation_policy_dto = api.model(
        "Escalation Policy Dto",
        {
            "display_order": fields.Integer(min=1, max=2, required=True),
            "delay": fields.Integer(required=True),
            "from_priority": fields.Integer(min=0, max=1, required=True),
            "to_priority": fields.Integer(min=1, max=2, required=True),
        },
    )

    task_type_response = api.model(
        "Task Type Response",
        {
            "id": fields.Integer(),
            "label": fields.String(),
            "default_time_estimate": fields.Integer(min=0),
            "default_description": fields.String(),
            "default_priority": fields.Integer(enum=[1, 2, 3]),
            "org_id": fields.Integer(),
            "disabled": NullableDateTime,
            "tooltip": fields.String(),
            "escalation_policies": fields.List(fields.Nested(escalation_policy_dto)),
        },
    )

    get_response_dto = api.model(
        "Get Task Types Response", {"task_types": fields.List(fields.Nested(task_type_response))}
    )

    @requires_jwt
    @authorize(Operations.GET, Resources.TASK_TYPES)
    @api.marshal_with(get_response_dto, code=200)
    def get(self, **kwargs):
        """Returns all task types"""
        req_user = kwargs["req_user"]

        with session_scope() as session:
            task_type_query = (
                session.query(TaskType)
                .filter(and_(TaskType.org_id == req_user.org_id, TaskType.disabled == None))  # noqa
                .all()
            )

        task_types = [tt.fat_dict() for tt in task_type_query]
        req_user.log(operation=Operations.GET, resource=Resources.TASK_TYPES)
        return {"task_types": task_types}, 200

    create_request = api.model(
        "Create Task Type Request",
        {
            "label": fields.String(required=True),
            "default_time_estimate": fields.Integer(min=-1, required=True),
            "default_priority": fields.Integer(enum=[-1, 0, 1, 2], required=True),
            "default_description": fields.String(),
            "escalation_policies": fields.List(fields.Nested(escalation_policy_dto), required=True, min_items=0),
        },
    )

    @requires_jwt
    @authorize(Operations.CREATE, Resources.TASK_TYPE)
    @api.expect(create_request, validate=True)
    @api.response(204, "Success")
    def post(self, **kwargs):
        """Creates a task type"""
        req_user = kwargs["req_user"]
        request_body = request.get_json()

        # check if the type already exists
        with session_scope() as session:
            task_type = (
                session.query(TaskType)
                .filter(
                    func.lower(TaskType.label) == func.lower(request_body["label"]), TaskType.org_id == req_user.org_id
                )
                .first()
            )

        if task_type is None:
            # it didn't exist so just create it
            with session_scope() as session:
                new_task_type = TaskType(
                    label=request_body["label"],
                    org_id=req_user.org_id,
                    disabled=None,
                    default_time_estimate=request_body["default_time_estimate"],
                    default_priority=request_body["default_priority"],
                    default_description=request_body.get("default_description"),
                )
                session.add(new_task_type)

            for escalation in request_body["escalation_policies"]:
                self.check_task_priority(escalation["from_priority"])
                self.check_task_priority(escalation["to_priority"])
                self._create_escalation(req_user, new_task_type, escalation)

            Activity(
                org_id=req_user.org_id,
                event=Events.tasktype_created,
                event_id=new_task_type.id,
                event_friendly=f"Created task type {request_body['label']}",
            )
            req_user.log(operation=Operations.CREATE, resource=Resources.TASK_TYPE, resource_id=new_task_type.id)
        else:
            # it existed so check if it needs to be enabled
            if task_type.disabled is None:
                raise ValidationError(f"Task type {request_body['label']} already exists.")
            with session_scope():
                task_type.disabled = None
            Activity(
                org_id=req_user.org_id,
                event=Events.tasktype_enabled,
                event_id=task_type.id,
                event_friendly=f"Enabled task type {request_body['label']}",
            )
            req_user.log(operation=Operations.ENABLE, resource=Resources.TASK_TYPE, resource_id=task_type.id)

        return "", 204

    update_request = api.model(
        "Update Task Type Request",
        {
            "id": fields.Integer(required=True),
            "label": fields.String(required=True),
            "default_time_estimate": fields.Integer(min=-1, required=True),
            "default_priority": fields.Integer(enum=[-1, 0, 1, 2], required=True),
            "default_description": fields.String(),
            "escalation_policies": fields.List(fields.Nested(escalation_policy_dto), required=True, min_items=0),
        },
    )

    @requires_jwt
    @authorize(Operations.UPDATE, Resources.TASK_TYPE)
    @api.expect(update_request, validate=True)
    @api.response(204, "Success")
    def put(self, **kwargs):
        """Updates a task type"""
        req_user = kwargs["req_user"]
        request_body = request.get_json()

        # check that the task type exists
        with session_scope() as session:
            task_type = (
                session.query(TaskType).filter_by(id=request_body["id"], org_id=req_user.org_id, disabled=None).first()
            )

        if task_type is None:
            raise ResourceNotFoundError(f"Task type {request_body['label']} doesn't exist.")

        # update label and defaults
        with session_scope():
            task_type.label = request_body["label"]
            task_type.default_time_estimate = request_body["default_time_estimate"]
            task_type.default_priority = request_body["default_priority"]
            task_type.default_description = request_body.get("default_description")

        for escalation in request_body["escalation_policies"]:
            self.check_task_priority(escalation["from_priority"])
            self.check_task_priority(escalation["to_priority"])

            with session_scope() as session:
                escalation_exists = session.query(
                    exists().where(
                        and_(
                            TaskTypeEscalation.task_type_id == task_type.id,
                            TaskTypeEscalation.display_order == escalation["display_order"],
                        )
                    )
                ).scalar()

                if escalation_exists:
                    self._update_escalation(req_user, task_type, escalation)
                else:
                    self._create_escalation(req_user, task_type, escalation)

        # DELETE MISMATCHING ESCALATIONS
        # get escalations in request as a set of tuples
        request_escalations = {(task_type.id, e.get("display_order")) for e in request_body["escalation_policies"]}

        with session_scope() as session:
            # get escalations which exist in the db as a set of tuples
            db_esc_qry = (
                session.query(TaskTypeEscalation.task_type_id, TaskTypeEscalation.display_order)
                .filter_by(task_type_id=task_type.id)
                .all()
            )
            db_escalations = {e for e in db_esc_qry}

            # remove those that exist in the db that didn't in the request
            to_remove = db_escalations - request_escalations
            for r in to_remove:
                session.query(TaskTypeEscalation).filter_by(task_type_id=r[0], display_order=r[1]).delete(
                    synchronize_session=False
                )
                current_app.logger.info(f"deleted task type escalation with task_type_id:{r[0]}, display_order:{r[1]}")

        return "", 204

    @staticmethod
    def _create_escalation(req_user, task_type, escalation):
        """Create an escalation"""
        with session_scope() as session:
            new_escalation = TaskTypeEscalation(
                task_type_id=task_type.id,
                display_order=escalation["display_order"],
                delay=escalation["delay"],
                from_priority=escalation["from_priority"],
                to_priority=escalation["to_priority"],
            )
            session.add(new_escalation)

        Activity(org_id=req_user.org_id, event=Events.tasktype_escalation_created, event_id=task_type.id).publish()
        Activity(
            org_id=req_user.org_id,
            event=Events.user_created_tasktype_escalation,
            event_id=req_user.id,
            event_friendly=f"Created escalation for {task_type.label}.",
        ).publish()
        req_user.log(
            operation=Operations.CREATE, resource=Resources.TASK_TYPE_ESCALATION, resource_id=task_type.id,
        )
        current_app.logger.info(f"created task type escalation {new_escalation.as_dict()}")

    @staticmethod
    def _update_escalation(req_user, task_type, escalation):
        """Update an escalation"""
        with session_scope() as session:
            escalation_to_update = (
                session.query(TaskTypeEscalation)
                .filter_by(task_type_id=task_type.id, display_order=escalation["display_order"])
                .first()
            )
            escalation_to_update.display_order = escalation["display_order"]
            escalation_to_update.delay = escalation["delay"]
            escalation_to_update.from_priority = escalation["from_priority"]
            escalation_to_update.to_priority = escalation["to_priority"]

        Activity(org_id=req_user.org_id, event=Events.tasktype_escalation_updated, event_id=task_type.id).publish()
        Activity(
            org_id=req_user.org_id,
            event=Events.user_updated_tasktype_escalation,
            event_id=req_user.id,
            event_friendly=f"Updated escalation for {task_type.label}.",
        ).publish()
        req_user.log(
            operation=Operations.UPDATE, resource=Resources.TASK_TYPE_ESCALATION, resource_id=task_type.id,
        )
        current_app.logger.info(f"updated task type escalation {escalation_to_update.as_dict()}")


@api.route("/<int:task_type_id>")
class DeleteTaskType(RequestValidationController):
    @requires_jwt
    @authorize(Operations.DISABLE, Resources.TASK_TYPE)
    @api.response(204, "Success")
    def delete(self, task_type_id, **kwargs):
        """Disables a task type"""
        req_user = kwargs["req_user"]

        with session_scope() as session:
            task_type = session.query(TaskType).filter_by(id=task_type_id).first()

        if task_type is None:
            raise ResourceNotFoundError(f"Task type {task_type_id} doesn't exist.")

        with session_scope():
            task_type.disabled = datetime.datetime.utcnow()

        Activity(org_id=task_type.org_id, event=Events.tasktype_disabled, event_id=task_type.id,).publish()
        Activity(
            org_id=req_user.org_id,
            event=Events.user_disabled_tasktype,
            event_id=req_user.id,
            event_friendly=f"Disabled task type {task_type.label}.",
        ).publish()
        req_user.log(operation=Operations.DISABLE, resource=Resources.TASK_TYPE, resource_id=task_type.id)
        return "", 204
