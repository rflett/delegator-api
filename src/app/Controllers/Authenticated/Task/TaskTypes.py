import datetime

from flask import request, Response
from flask_restplus import Namespace

from app import logger, session_scope
from app.Controllers.Base import RequestValidationController
from app.Decorators import requires_jwt, handle_exceptions, authorize
from app.Models import TaskType, TaskTypeEscalation, Activity
from app.Models.Enums import Events, Operations, Resources
from app.Models.Request import disable_task_type_request, update_task_type_request, create_task_type_request
from app.Models.Response import task_types_response, task_type_response, message_response_dto
from app.Exceptions import ValidationError

task_types_route = Namespace(
    path="/tasks/types",
    name="Task Types",
    description="Manage Task Types"
)


@task_types_route.route("/")
class TaskTypes(RequestValidationController):

    @handle_exceptions
    @requires_jwt
    @authorize(Operations.GET, Resources.TASK_TYPE)
    @task_types_route.response(200, "Success", task_types_response)
    def get(self, **kwargs) -> Response:
        """Returns all task types"""
        req_user = kwargs['req_user']

        with session_scope() as session:
            task_type_query = session.query(TaskType).filter_by(org_id=req_user.org_id).all()

        task_types = [tt.fat_dict() for tt in task_type_query]
        req_user.log(
            operation=Operations.GET,
            resource=Resources.TASK_TYPES
        )
        return self.ok({"task_types": task_types})

    @handle_exceptions
    @requires_jwt
    @authorize(Operations.CREATE, Resources.TASK_TYPE)
    @task_types_route.expect(create_task_type_request)
    @task_types_route.response(200, "Success", task_type_response)
    @task_types_route.response(400, "Failed to create the task type", message_response_dto)
    def post(self, **kwargs) -> Response:
        """Creates a task type"""
        req_user = kwargs['req_user']

        label, task_type = self.validate_create_task_type_request(request.get_json(), **kwargs)

        if task_type is None:
            # it didn't exist so just create it
            with session_scope() as session:
                new_task_type = TaskType(
                    label=label,
                    org_id=req_user.org_id,
                )
                session.add(new_task_type)
            Activity(
                org_id=req_user.org_id,
                event=Events.tasktype_created,
                event_id=new_task_type.id,
                event_friendly=f"Created task type {label}"
            )
            req_user.log(
                operation=Operations.CREATE,
                resource=Resources.TASK_TYPE,
                resource_id=new_task_type.id
            )
            return self.created(new_task_type.fat_dict())
        else:
            # it existed so check if it needs to be enabled
            if task_type.disabled is None:
                raise ValidationError(f"Task type {label} already exists.")
            with session_scope():
                task_type.disabled = None
            Activity(
                org_id=req_user.org_id,
                event=Events.tasktype_enabled,
                event_id=task_type.id,
                event_friendly=f"Enabled task type {label}"
            )
            req_user.log(
                operation=Operations.ENABLE,
                resource=Resources.TASK_TYPE,
                resource_id=task_type.id
            )
            return self.created(task_type.fat_dict())

    @handle_exceptions
    @requires_jwt
    @authorize(Operations.UPDATE, Resources.TASK_TYPE)
    @task_types_route.expect(update_task_type_request)
    @task_types_route.response(200, "Success", task_type_response)
    @task_types_route.response(400, "Failed to update the task type", message_response_dto)
    def put(self, **kwargs) -> Response:
        """Updates a task type"""
        req_user = kwargs['req_user']
        request_body = request.get_json()

        task_type_to_update, escalations = self.validate_update_task_type_request(
            org_id=req_user.org_id,
            request_body=request_body
        )

        # counter for number of task types created/updated/deleted in this request
        total_updated = total_created = total_deleted = 0

        # update label
        if task_type_to_update.label != request_body['label']:
            with session_scope():
                task_type_to_update.label = request_body['label']

        # UPSERT ESCALATIONS
        for escalation in escalations:
            if escalation['action'] == 'create':
                total_created += 1
                with session_scope() as session:
                    new_escalation = TaskTypeEscalation(
                        task_type_id=task_type_to_update.id,
                        display_order=escalation['display_order'],
                        delay=escalation['delay'],
                        from_priority=escalation['from_priority'],
                        to_priority=escalation['to_priority']
                    )
                    session.add(new_escalation)

                Activity(
                    org_id=req_user.org_id,
                    event=Events.tasktype_escalation_created,
                    event_id=task_type_to_update.id
                ).publish()
                Activity(
                    org_id=req_user.org_id,
                    event=Events.user_created_tasktype_escalation,
                    event_id=req_user.id,
                    event_friendly=f"Created escalation for {task_type_to_update.label}."
                ).publish()
                req_user.log(
                    operation=Operations.CREATE,
                    resource=Resources.TASK_TYPE_ESCALATION,
                    resource_id=task_type_to_update.id
                )
                logger.info(f"created task type escalation {new_escalation.as_dict()}")

            elif escalation['action'] == 'update':
                total_updated += 1

                with session_scope() as session:
                    escalation_to_update = session.query(TaskTypeEscalation).filter_by(
                        task_type_id=task_type_to_update.id,
                        display_order=escalation['display_order']
                    ).first()

                    for k, v in escalation.items():
                        escalation_to_update.__setattr__(k, v)

                Activity(
                    org_id=req_user.org_id,
                    event=Events.tasktype_escalation_updated,
                    event_id=task_type_to_update.id
                ).publish()
                Activity(
                    org_id=req_user.org_id,
                    event=Events.user_created_tasktype_escalation,
                    event_id=req_user.id,
                    event_friendly=f"Updated escalation for {task_type_to_update.label}."
                ).publish()
                req_user.log(
                    operation=Operations.UPDATE,
                    resource=Resources.TASK_TYPE_ESCALATION,
                    resource_id=task_type_to_update.id
                )
                logger.info(f"updated task type escalation {escalation_to_update.as_dict()}")

        # DELETE MISMATCHING ESCALATIONS
        # get escalations in request as a set of tuples
        request_escalations = {(task_type_to_update.id, e.get('display_order')) for e in escalations}

        with session_scope() as session:
            # get escalations which exist in the db as a set of tuples
            db_esc_qry = session.query(TaskTypeEscalation.task_type_id, TaskTypeEscalation.display_order)\
                .filter_by(task_type_id=task_type_to_update.id).all()
            db_escalations = {e for e in db_esc_qry}

            # remove those that exist in the db that didn't in the request
            to_remove = db_escalations - request_escalations
            for r in to_remove:
                total_deleted += 1
                session.query(TaskTypeEscalation).filter_by(
                    task_type_id=r[0],
                    display_order=r[1]
                ).delete(synchronize_session=False)
                logger.info(f"deleted task type escalation with task_type_id:{r[0]}, display_order:{r[1]}")

        logger.info(f"upsert task type escalations finished. "
                    f"created:{total_created}, updated:{total_updated}, deleted:{total_deleted}")
        # SUCCESS
        return self.ok(task_type_to_update.fat_dict())

    @handle_exceptions
    @requires_jwt
    @authorize(Operations.DISABLE, Resources.TASK_TYPE)
    @task_types_route.expect(disable_task_type_request)
    @task_types_route.response(200, "Success", task_type_response)
    @task_types_route.response(400, "Failed to disable the task type", message_response_dto)
    def delete(self, **kwargs) -> Response:
        """Disables a task type"""
        req_user = kwargs['req_user']
        request_body = request.get_json()
        task_type_id = request_body.get('id')

        task_type_to_disable = self.validate_disable_task_type_request(task_type_id)

        with session_scope():
            task_type_to_disable.disabled = datetime.datetime.utcnow()

        Activity(
            org_id=task_type_to_disable.org_id,
            event=Events.tasktype_disabled,
            event_id=task_type_to_disable.id,
        ).publish()
        Activity(
            org_id=req_user.org_id,
            event=Events.user_disabled_tasktype,
            event_id=req_user.id,
            event_friendly=f"Disabled task type {task_type_to_disable.label}."
        ).publish()
        req_user.log(
            operation=Operations.DISABLE,
            resource=Resources.TASK_TYPE,
            resource_id=task_type_to_disable.id
        )
        return self.ok(task_type_to_disable.fat_dict())
