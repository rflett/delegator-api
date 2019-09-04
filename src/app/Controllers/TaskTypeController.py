import datetime

from flask import request, Response

from app import logger, session_scope, g_response, j_response
from app.Models import TaskType, TaskTypeEscalation, Activity
from app.Models.Enums import Events, Operations, Resources


def _get_task_type_escalation(task_type_id: int, display_order: int):
    """Gets a task type escalation """
    with session_scope() as session:
        ret = session.query(TaskTypeEscalation).filter_by(
                task_type_id=task_type_id,
                display_order=display_order
        ).first()
    if ret is None:
        logger.info(f"No task type escalation for task_type {task_type_id} and display order {display_order}.")
        raise ValueError(f"No task type escalation with "
                         f"task_type_id {task_type_id} and display order {display_order}")
    else:
        return ret


class TaskTypeController(object):
    @staticmethod
    def get_task_types(req: request) -> Response:
        """Returns all task types """
        from app.Controllers import AuthorizationController, AuthenticationController
        from app.Models import TaskType

        req_user = AuthenticationController.get_user_from_request(req.headers)

        AuthorizationController.authorize_request(
            auth_user=req_user,
            operation=Operations.GET,
            resource=Resources.TASK_TYPES
        )

        with session_scope() as session:
            task_type_query = session\
                .query(TaskType)\
                .filter_by(
                    org_id=req_user.org_id
                ).all()

        task_types = [tt.fat_dict() for tt in task_type_query]
        req_user.log(
            operation=Operations.GET,
            resource=Resources.TASK_TYPES
        )
        return j_response(task_types)

    @staticmethod
    def create_task_type(req: request) -> Response:
        """Creates a task type"""
        from app.Controllers import AuthorizationController, ValidationController, AuthenticationController

        req_user = AuthenticationController.get_user_from_request(req.headers)
        request_body = req.get_json()

        label, task_type = ValidationController.validate_create_task_type_request(req_user.org_id, request_body)

        if task_type is None:
            # it didn't exist so just create it
            AuthorizationController.authorize_request(
                auth_user=req_user,
                operation=Operations.CREATE,
                resource=Resources.TASK_TYPE
            )
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
            return g_response(f"Created {label}", status=201)
        else:
            # it existed so check if it needs to be enabled
            if task_type.disabled is None:
                return g_response(f"Task type {label} already exists.", status=400)
            AuthorizationController.authorize_request(
                auth_user=req_user,
                operation=Operations.ENABLE,
                resource=Resources.TASK_TYPE
            )
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
            return g_response(f"Enabled {label}")

    @staticmethod
    def update_task_type(req: request) -> Response:
        """Updates a task type"""
        from app.Controllers import AuthorizationController, ValidationController, AuthenticationController

        req_user = AuthenticationController.get_user_from_request(req.headers)
        request_body = req.get_json()

        AuthorizationController.authorize_request(
            auth_user=req_user,
            operation=Operations.UPDATE,
            resource=Resources.TASK_TYPE
        )

        task_type_to_update, escalations = ValidationController.validate_update_task_type_request(
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
                escalation_to_update = _get_task_type_escalation(
                    task_type_id=task_type_to_update.id,
                    display_order=escalation['display_order']
                )
                with session_scope():
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
        return g_response(status=204)

    @staticmethod
    def disable_task_type(task_type_id: int, req: request) -> Response:
        """Disables a task type """
        from app.Controllers import AuthorizationController, ValidationController, AuthenticationController

        req_user = AuthenticationController.get_user_from_request(req.headers)

        AuthorizationController.authorize_request(
            auth_user=req_user,
            operation=Operations.DISABLE,
            resource=Resources.TASK_TYPE
        )

        task_type_to_disable = ValidationController.validate_disable_task_type_request(req_user.org_id, task_type_id)

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
        return g_response(status=204)
