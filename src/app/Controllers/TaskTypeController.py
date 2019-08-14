import datetime

from flask import request, Response
from sqlalchemy import exists, func

from app import logger, session_scope, g_response, j_response
from app.Exceptions import ValidationError
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


def _get_task_type_by_id(org_id: int, task_type_id: int) -> TaskType:
    """Gets a task type by its id """
    with session_scope() as session:
        ret = session.query(TaskType).filter_by(
            id=task_type_id,
            org_id=org_id
        ).first()
    if ret is None:
        logger.info(f"Task type with id {task_type_id} does not exist.")
        raise ValueError(f"Task type with id {task_type_id} does not exist.")
    else:
        return ret


class TaskTypeController(object):
    @staticmethod
    def task_type_exists(task_type_identifier: int) -> bool:
        """Checks to see if a task type exists. """
        with session_scope() as session:
            if isinstance(task_type_identifier, int):
                return session.query(exists().where(
                    TaskType.id == task_type_identifier
                )).scalar()
            else:
                raise ValidationError("Task type id not supplied.")

    @staticmethod
    def get_task_type_by_id(org_id: int, task_type_id: int) -> TaskType:
        """Gets a task type by its id """
        return _get_task_type_by_id(org_id, task_type_id)

    @staticmethod
    def get_task_type_by_label(label: str, org_id: int) -> TaskType:
        """Gets a task type by its label """
        with session_scope() as session:
            ret = session.query(TaskType).filter(
                func.lower(TaskType.label) == func.lower(label),
                TaskType.org_id == org_id
            ).first()
        if ret is None:
            logger.info(f"Task type with label {label} does not exist in org {org_id}.")
            raise ValueError(f"Task type with label {label} does not exist in org {org_id}.")
        else:
            return ret

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
                    org_id=req_user.org_id,
                    disabled=None
                ).all()

        task_types = [tt.fat_dict() for tt in task_type_query]
        req_user.log(
            operation=Operations.GET,
            resource=Resources.TASK_TYPES
        )
        return j_response(task_types)

    @staticmethod
    def create_task_type(req: request) -> Response:
        """Create a task type """
        from app.Controllers import AuthorizationController, ValidationController, AuthenticationController
        from app.Models import TaskType

        req_user = AuthenticationController.get_user_from_request(req.headers)
        request_body = req.get_json()

        AuthorizationController.authorize_request(
            auth_user=req_user,
            operation=Operations.CREATE,
            resource=Resources.TASK_TYPE
        )

        # validate task type request
        validate_res = ValidationController.validate_create_task_type_request(req_user.org_id, request_body)

        if isinstance(validate_res, str):
            # create the task type because it doesn't exist
            with session_scope() as session:
                task_type = TaskType(
                    label=validate_res,
                    org_id=req_user.org_id
                )
                session.add(task_type)
            Activity(
                org_id=task_type.org_id,
                event=Events.tasktype_created,
                event_id=task_type.id,
            ).publish()
            Activity(
                org_id=req_user.org_id,
                event=Events.user_created_tasktype,
                event_id=req_user.id,
                event_friendly=f"Created task type {task_type.label}."
            ).publish()
            req_user.log(
                operation=Operations.CREATE,
                resource=Resources.TASK_TYPE,
                resource_id=task_type.id
            )
            logger.info(f"created task type {task_type.as_dict()}")
        elif isinstance(validate_res, TaskType):
            # enable the task type because it exists
            if validate_res.disabled is not None:
                # it's disabled, so it will need to be enabled
                with session_scope():
                    AuthorizationController.authorize_request(
                        auth_user=req_user,
                        operation=Operations.ENABLE,
                        resource=Resources.TASK_TYPE
                    )

                    validate_res.disabled = None

                Activity(
                    org_id=validate_res.org_id,
                    event=Events.tasktype_enabled,
                    event_id=validate_res.id
                ).publish()
                req_user.log(
                    operation=Operations.ENABLE,
                    resource=Resources.TASK_TYPE,
                    resource_id=validate_res.id
                )
                logger.info(f"Enabled task type {validate_res.as_dict()}")

        # counter for number of task types created/updated/deleted in this request
        total_updated = total_created = total_deleted = 0

        # VALIDATION
        escalations = request_body.get('escalation_policies')
        if escalations is None:
            # there are no esclations to handle
            return g_response("Successfully created task type", 201)
        elif not isinstance(escalations, list):
            # the escalations were not provided as a list
            raise ValidationError("escalations property is not a list.")
        else:
            # there's escalations in the request, so add and remove them as required
            if isinstance(validate_res, str):
                task_type_id = task_type.id
            else:
                task_type_id = validate_res.id

            valid_escalations = ValidationController.validate_upsert_task_escalation(task_type_id, escalations)

            # UPSERT
            for escalation in valid_escalations:
                if escalation.get('action') == 'create':
                    total_created += 1
                    with session_scope() as session:
                        new_escalation = TaskTypeEscalation(
                            task_type_id=task_type_id,
                            display_order=escalation.get('display_order'),
                            delay=escalation.get('delay'),
                            from_priority=escalation.get('from_priority'),
                            to_priority=escalation.get('to_priority')
                        )
                        session.add(new_escalation)

                    Activity(
                        org_id=req_user.org_id,
                        event=Events.tasktype_escalation_created,
                        event_id=task_type_id
                    ).publish()
                    Activity(
                        org_id=req_user.org_id,
                        event=Events.user_created_tasktype_escalation,
                        event_id=req_user.id,
                        event_friendly=f"Created escalation for task type "
                        f"{_get_task_type_by_id(req_user.org_id, task_type_id).label}."
                    ).publish()
                    req_user.log(
                        operation=Operations.CREATE,
                        resource=Resources.TASK_TYPE_ESCALATION,
                        resource_id=task_type_id
                    )
                    logger.info(f"created task type escalation {new_escalation.as_dict()}")

                elif escalation.get('action') == 'update':
                    total_updated += 1
                    escalation_to_update = _get_task_type_escalation(
                        task_type_id=task_type_id,
                        display_order=escalation.get('display_order')
                    )
                    with session_scope():
                        for k, v in escalation.items():
                            escalation_to_update.__setattr__(k, v)

                        Activity(
                            org_id=req_user.org_id,
                            event=Events.tasktype_escalation_updated,
                            event_id=task_type_id
                        ).publish()
                        Activity(
                            org_id=req_user.org_id,
                            event=Events.user_created_tasktype_escalation,
                            event_id=req_user.id,
                            event_friendly=f"Updated escalation for task type "
                            f"{_get_task_type_by_id(req_user.org_id, task_type_id).label}."
                        ).publish()
                        req_user.log(
                            operation=Operations.UPDATE,
                            resource=Resources.TASK_TYPE_ESCALATION,
                            resource_id=task_type_id
                        )
                    logger.info(f"updated task type escalation {escalation_to_update.as_dict()}")

            # DELETE MISMATCH
            # get escalations in request as a set of tuples
            request_escalations = {(task_type_id, e.get('display_order')) for e in valid_escalations}

            with session_scope() as session:
                # get escalations which exist in the db as a set of tuples
                db_esc_qry = session.query(TaskTypeEscalation.task_type_id, TaskTypeEscalation.display_order)\
                    .filter_by(task_type_id=task_type_id).all()
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

        valid_dtt = ValidationController.validate_disable_task_type_request(req_user.org_id, task_type_id)

        with session_scope():
            valid_dtt.disabled = datetime.datetime.utcnow()

        Activity(
            org_id=valid_dtt.org_id,
            event=Events.tasktype_disabled,
            event_id=valid_dtt.id,
        ).publish()
        Activity(
            org_id=req_user.org_id,
            event=Events.user_disabled_tasktype,
            event_id=req_user.id,
            event_friendly=f"Disabled task type {valid_dtt.label}."
        ).publish()
        req_user.log(
            operation=Operations.DISABLE,
            resource=Resources.TASK_TYPE,
            resource_id=valid_dtt.id
        )
        return g_response(status=204)
